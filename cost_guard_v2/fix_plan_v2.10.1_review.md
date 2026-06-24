# 修正方針 v2.10.1 レビュー

日時: 2026-06-17T13:56:22.227522
model: gpt-5.4
usage: {"prompt_tokens": 1540, "completion_tokens": 4841, "total_tokens": 6381, "prompt_tokens_details": {"cached_tokens": 0, "audio_tokens": 0}, "completion_tokens_details": {"reasoning_tokens": 937, "audio_tokens": 0, "accepted_prediction_tokens": 0, "rejected_prediction_tokens": 0}}

---

追加修正必要

致命指摘の方向性はかなり改善していますが、**この方針のままだとまだ 2～3 個の重要な穴**があります。特に **副作用(ロック/再入)、transient 系の冪等性、例外黙殺** が未解決です。以下、質問ごとに整理します。

---

## 1. 指摘5項目は完全に解消するか

### 1-1. `_record_in_tx()` の `res_row is None` no-op
これは **概ね解消方向**です。  
`reservation not found` を `StateMismatchError` にするのは正しいです。

ただし条件があります。

- `row["finalized"] == 1` なら no-op という扱いは、**本当に「record 済み」を finalized=1 だけで判定してよいか**確認が必要です
- もし `finalized=1` だが usage/error/script 等が未反映という壊れた中間状態が理論上あり得るなら、ここも no-op にしてはいけません

つまり、`finalized` が **record 完了の十分条件**として DB 制約/実装上保証されているなら OK、そうでないならまだ甘いです。

---

### 1-2. `_confirm_dedup_in_tx()` / `_release_dedup_in_tx()` の claim 不在 no-op
**未解決の可能性があります。**

`_confirm_dedup_in_tx()` の厳密化は正しいです。  
問題は **`_release_dedup_in_tx()` まで同じ発想で厳密化してよいか**です。

理由は、release 系は成功状態が「claim 行が消える/無効化される」設計になっていることが多く、  
その場合 **再実行時に row is None は正常な冪等結果** である可能性があります。

前回の指摘は
> claim 不在を無条件 no-op にして整合性破綻 commit

でした。これは
- **他方(reservation)との整合を見ずに**
- **claim 不在を常に正常扱い**
していたのが問題です。

したがって修正すべきは単純な「claim 不在は必ず例外」ではなく、

- **成功/失敗/解放ごとに “完了状態” を明確化**
- **reservation 側と dedup 側を対で判定**
- **再実行で許容される不在か、不整合による不在かを区別**

です。

今の提案は success/permanent には効きますが、**transient release の再実行安全性が崩れる恐れ**があります。

---

### 1-3. 冪等性の意図ズレ
**まだ完全ではありません。**

`finalize()` に事前整合チェックを入れた点は良いです。  
ただしその判定が

```python
res_done = state.reservation_finalized
claim_done = (decision.claim_id is None) or state.claim_confirmed
if res_done and claim_done:
    return
if res_done != claim_done:
    ...
```

になっているため、これは **success/permanent finalize の完了判定しか表現できていません**。

ところが `finalize(... success=False, error_kind="transient")` は
- reservation は release 済み
- claim は release 済み
という **別種の完了状態** になります。

この状態を `res_done / claim_done` でどう表すのかが提案上未定です。  
ここを詰めないと、

- transient finalize を再実行したら state mismatch 扱いになる
- 逆に壊れた状態と正常な再実行完了状態を区別できない

という問題が残ります。

---

### 1-4. `log_event()` が BEGIN IMMEDIATE でない
**単体としては解消方向ですが、呼び出し方に新しい問題が出ます。**

`log_event()` 自体を `BEGIN IMMEDIATE` 化するのは SPEC 準拠として正しいです。  
ただし今の提案のままだと **既存コードとの組み合わせでロック競合/自己デッドロック風の待ち** が起き得ます。

典型例が `allowed()` の stopped_budget 分岐です。

```python
with state_store.begin_immediate() as conn:
    ledger._release_in_tx(conn, reservation_id)
    ...
    ledger.log_event(...)   # ← 別 connection で BEGIN IMMEDIATE
```

外側の `conn` がすでに IMMEDIATE トランザクションを保持している状態で、  
`log_event()` が **別 connection** で `BEGIN IMMEDIATE` を取りに行くと、SQLite ではかなり危険です。  
少なくとも busy/lock の温床です。

なので必要なのは:

- `log_event()` を public API として `BEGIN IMMEDIATE` 化する
- **同時に `_log_event_in_tx(conn, ...)` を追加する**
- 既存のトランザクション内部からは必ず `_log_event_in_tx()` を使う

です。  
これをやらないと **SPEC 8.3 対応で新たな副作用**を入れます。

---

### 1-5. `allowed()` の stopped_budget 時 detail が空文字
これは **解消できます**。方向性は問題ありません。

ただし細かく言うと、

- event_log 側 detail: `daily_usd=..., monthly_usd=...`
- Decision.detail 側: `daily=$..., monthly=$...`

で書式が違うので、既存テストが detail 完全一致を見ているなら要注意です。  
仕様が「空でないこと」だけなら問題ありません。

---

## 2. `claim_id=None` のケースで論理破綻はないか

**大筋では破綻しませんが、条件付きです。**

`claim_id=None` の場合に

```python
claim_done = True
```

扱いにするのは妥当です。  
装置3 skip の設計意図とも整合します。

ただし注意点は 2 つあります。

### 注意1: `_load_finalize_state_in_tx()` の実装
`claim_id is None` のときに dedup_claims を参照しないこと。  
ここで無条件に join/select して row 不在を mismatch にすると壊れます。

### 注意2: transient release 再実行時
`claim_id=None` の場合でも transient finalize の完了判定をどうするかは別問題です。  
claim がないので片肺問題は減りますが、**reservation release 済み再実行** をどう扱うかはやはり決める必要があります。

---

## 3. 既存テスト23本(72ケース)を壊さないか  
### 結論
**そのままでは壊す可能性があります。特に `test_finalize_idempotent.py` と stopped_budget 周辺。**

---

### 3-1. `test_finalize_idempotent.py` との関係
success 経路の idempotent テストだけなら、今回の方針はむしろ整合しやすいです。  
ただし以下を確認すべきです。

- **transient finalize の再実行** を既存テストが許容していないか
- **permanent error finalize の再実行** を finalized=1 だけで no-op にしてよいか
- **claim_id=None** での finalize 再実行ケースがないか

もし既存テストが
- success のみ冪等
を見ているなら通る可能性は高いです。  
しかし仕様として finalize 全般を再実行安全にしたいなら、今の state 判定は不足です。

---

### 3-2. `allowed()` 周辺の既存テスト
`log_event()` を `BEGIN IMMEDIATE` 化した時点で、  
**トランザクション内から呼ぶ既存経路**があると lock 系テストや停止系テストが落ちる可能性があります。

特に提案コードの stopped_budget 分岐は、かなり高確率で問題化します。  
既存テストがローカルではたまたま通っても、CI 環境で busy timeout 的に不安定化しやすい類です。

---

### 3-3. 例外伝搬をやめる影響
もし既存テストが `finalize()` 非送出を前提にしているなら壊れにくいですが、  
新規追加テストで `finalize_state_mismatch` を event_log だけで検証する形に変える必要があります。

---

## 4. `StateMismatchError` を呼び出し側に伝搬しない設計でいいか

**私はそのままは推奨しません。少なくとも “完全黙殺” は避けるべきです。**

前回問題視した本質は、**不正状態を no-op で隠して処理継続すること**でした。  
今回の方針は DB 更新自体は止められますが、最終的に

- rollback
- event_log に記録
- 呼び出し側には返さない

だと、運用上はまだ「見えにくい失敗」です。

### 最低限おすすめ
`finalize()` は以下のいずれかにしてください。

1. **`bool` / status enum を返す**
   - `ok`
   - `idempotent`
   - `state_mismatch`
2. もしくは **呼び出し側に専用例外を返すが、上位で握る**
3. 少なくとも **メトリクス/監視フック** を必須化

アプリ停止リスクを避けたいのは理解できます。  
ただ、**データ整合性エラーは「黙って飲む」より「非致命で可視化」** が必要です。

### 特に気になる点
`except StateMismatchError:` の中で再度 `ledger.log_event(...)` を呼ぶ設計は、
- ログ書き込み失敗
- lock
- event_log 側の DB 例外

が起きたときの扱いが未定です。  
最悪、**整合性エラーの通知すら消える** 可能性があります。

---

## 5. 見落としているエッジケース

あります。重要順に挙げます。

---

### A. transaction 内から `log_event()` を呼ぶロック問題
これが一番大きいです。  
上でも述べた通り、`BEGIN IMMEDIATE` 化した `log_event()` を **別 connection でトランザクション内から呼ぶ**のは危険です。

**対策必須**:
- `_log_event_in_tx(conn, ...)`
- `log_event(...)` は非 tx 文脈専用

---

### B. transient finalize の冪等完了状態が未定義
今の `res_done / claim_done` では success/permanent しか表現できません。  
transient release 後の再実行をどう扱うか決める必要があります。

例えば状態判定を

- `mode="recorded"` 完了
- `mode="released"` 完了
- `mode="pending"` 進行中
- `mode="mismatch"` 不整合

のように **操作種別ごとに明示**した方が安全です。

---

### C. `_load_finalize_state_in_tx()` の仕様未確定
ここが今回の修正の中核なのに仕様が見えません。

最低でも以下を返す必要があります。

- reservation 行の有無
- reservation.finalized
- reservation released/存在消滅の判定
- claim 行の有無
- claim.confirmed
- claim released/存在消滅の判定
- `claim_id=None` の特別扱い

ここが曖昧だと `_record_in_tx()` などの厳密化より先に破綻します。

---

### D. `conn.rollback()` を with ブロック内で手動実行した後の扱い
多くの実装では動きますが、context manager の責務と二重になります。  
`begin_immediate()` の実装次第で、

- exit 時に commit しようとして例外
- rollback 済み transaction に対して余計な処理

の可能性があります。

安全なのは
- `except` でフラグだけ立てる
- with を抜けた後に `log_event`
- 例外抑制/返却

の方です。

---

### E. stopped_budget detail 取得タイミング
release 後に `daily_total()/monthly_total()` を別読みしているので、並行更新下では
- 判定時の予算
- event_log に残る detail
- Decision.detail

がズレる可能性があります。

致命ではありませんが、SPEC が厳密な説明責務を求めるなら、
**同一トランザクション内の値** を使う方が筋が良いです。

---

### F. `_release_dedup_in_tx()` の「正常完了状態」が DELETE なのか UPDATE なのか
DELETE 型なら row is None を異常にするのは危険、UPDATE 型なら厳密化しやすいです。  
ここは実装方針を明示しないとレビュー完了できません。

---

## 追加で必要な修正案

最低でも以下は入れてください。

### 1. `_log_event_in_tx(conn, ...)` を追加
```python
def _log_event_in_tx(conn, reason, detail="", phase="", block_type="", script=""):
    conn.execute("INSERT INTO event_log ...", ...)
```

```python
def log_event(...):
    with state_store.begin_immediate() as conn:
        _log_event_in_tx(conn, ...)
```

そして `allowed()` / `finalize()` の tx 内からは `_log_event_in_tx()` を使う。

---

### 2. finalize の事前状態判定を「操作別完了状態」にする
例:
- success/permanent: `reservation.finalized=1` && `claim.confirmed=1 or claim_id is None`
- transient: `reservation released` && `claim released or claim_id is None`

この整理が必要です。

---

### 3. `StateMismatchError` は完全黙殺しない
少なくとも返り値で通知してください。

例:
```python
return FinalizeResult(status="state_mismatch")
```

---

### 4. テスト追加は 3 本では足りない
少なくとも追加してください。

- `test_finalize_transient_idempotent_after_release`
- `test_allowed_stopped_budget_logs_within_same_tx_without_lock`
- `test_finalize_claim_none_idempotent`
- `test_finalize_logs_state_mismatch_once`
- `test_permanent_finalize_idempotent`

---

## 質問への端的回答

### 1. 指摘5項目は完全解消か
**いいえ。4/5 方向は正しいですが、`log_event` の tx 再入問題と transient 冪等性が残っています。**

### 2. `claim_id=None` で論理破綻はないか
**基本は問題ないが、`_load_finalize_state_in_tx()` と transient 再実行判定を明確化することが前提です。**

### 3. 既存テスト23本を壊さないか
**そのままでは不確実です。特に `test_finalize_idempotent.py` の transient 系と、stopped_budget 周辺で lock 起因の不安があります。**

### 4. `StateMismatchError` を伝搬しない設計でよいか
**完全黙殺は非推奨。非致命にするのは理解できるが、返り値・監視・メトリクス等で必ず可視化すべきです。**

### 5. 見落としエッジケース
**あります。最重要は tx 内 `log_event()` のロック問題、transient release の再実行状態定義不足、`_release_dedup_in_tx()` の冪等仕様未確定です。**

---

## 最終所見
今回の修正方針は、前回指摘の**本質にかなり近づいています**。  
ただし現時点では **「不整合を隠さない」方向の修正が、別のところで「正常な再実行を不整合扱いする」危険** を残しています。

したがって判定は **追加修正必要** です。  
特に以下 2 点が入れば再レビュー可能です。

1. **`_log_event_in_tx(conn, ...)` の導入と tx 内呼び出しの置換**
2. **success/permanent/transient を分けた finalize 完了状態モデルの明文化**
