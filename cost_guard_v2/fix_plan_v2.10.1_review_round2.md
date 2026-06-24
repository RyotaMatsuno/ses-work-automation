# 強化版修正方針 v2.10.1 レビュー(round 2)

日時: 2026-06-17T13:59:49.701231
model: gpt-5.4
usage: {"prompt_tokens": 1422, "completion_tokens": 3501, "total_tokens": 4923, "prompt_tokens_details": {"cached_tokens": 0, "audio_tokens": 0}, "completion_tokens_details": {"reasoning_tokens": 431, "audio_tokens": 0, "accepted_prediction_tokens": 0, "rejected_prediction_tokens": 0}}

---

【追加修正必要】

結論として、前回指摘の大半はかなり良く潰せていますが、**1点だけ本番GO前に必須の致命項目**があります。  
それは **STATE_MISMATCH 時の event_log 記録方法**です。

---

## 総評

今回の v2.10.1 は、前回の主要論点だった以下をかなり適切に補強できています。

- transient 冪等性
- tx 内 `log_event` 再入による自己ロック
- finalize 完了状態の表現統一
- finalize 返り値の可視化

この方向性自体は妥当で、**設計品質は前回より明確に改善**しています。  
ただし、**Step 5/6 の「_log_event_in_tx で mismatch を記録してから ROLLBACK」案は成立しません**。  
同一トランザクション内で書いた event_log は、その後 ROLLBACK すると消えます。

これは今回の設計意図
> `STATE_MISMATCH` を返しつつ event_log にも残す

を満たせないため、**このまま実装移行は不可**です。

---

# 1. 前回指摘は完全解消するか?

## 結論
**ほぼ解消。ただし `STATE_MISMATCH` の event_log 永続化だけ未解消**です。

### 解消できている点

#### 1) transient 冪等
かなり良いです。  
特に以下が効いています。

- transient 完了でも `reservations.finalized=1`
- claim 側も `confirmed!=0` で完了扱い
- idempotent 判定を state loader に寄せた

これで transient の再 finalize を通常成功系と同列に扱えるため、前回の穴はほぼ埋まっています。

---

#### 2) log_event の tx 再入
これも方向性は正しいです。

- `log_event()` を非 tx 用
- `_log_event_in_tx(conn, ...)` を tx 用

この切り分けで、`BEGIN IMMEDIATE` の二重取得問題は回避できます。  
`allowed()` の stopped_budget 記録もこの方式なら筋が通ります。

---

#### 3) state 仕様の明文化
`FinalizeState` の導入は良いです。  
とくに

- reservation の存在
- finalized 状態
- claim の存在
- confirmed 状態

を切り分けているため、`None` 扱いや片肺判定の曖昧さはかなり減ります。

---

#### 4) 返り値可視化
`FinalizeResult(status, detail)` も妥当です。  
「黙って何もしない」より運用上は明らかに良いです。

---

## 未解消の致命点

### `STATE_MISMATCH` を tx 内記録してから ROLLBACK するとログも消える
現案:

1. `BEGIN IMMEDIATE`
2. state 読み込み
3. mismatch 検出
4. `_log_event_in_tx(...)`
5. `ROLLBACK`
6. `STATE_MISMATCH` を返す

これは **4 の event_log INSERT/UPDATE が 5 で消える**ため、仕様どおりの「記録」になりません。

### 修正必須案
以下のどちらかにしてください。

#### 案A: rollback 後に別 tx で log_event()
- tx 内では mismatch 判定だけ行う
- `ROLLBACK`
- その後、新規接続/新規txで `log_event(...)`
- `FinalizeResult(STATE_MISMATCH, ...)` を返す

これが最も単純です。

#### 案B: mismatch 用ログは「ロールバックしない」
- mismatch 検出後、更新系を一切していないなら
- `_log_event_in_tx(...)` した後 `COMMIT`
- `STATE_MISMATCH` を返す

ただしこの場合、  
「mismatch は必ず rollback」という運用思想を捨てることになります。  
今回の方針文に「ROLLBACK 済み」と書いてあるので、整合性重視なら **案A** が無難です。

> 本番前提なら **案A推奨** です。

---

# 2. `release_dedup: DELETE → UPDATE(confirmed=1, error=2)` の副作用はないか?

## 結論
**設計としては妥当。ただし周辺参照箇所の総点検が GO 条件**です。

この変更のメリットは大きいです。

- transient でも完了状態を claim 側に残せる
- finalize 完了の統一判定がしやすい
- idempotent 判定が簡潔になる
- 「消したので状態が読めない」問題を避けられる

これは前回指摘への対処としてかなり良いです。

---

## ただし確認必須の副作用

### 1) `claims.error` に `2` を入れてよいか
以下を確認してください。

- DB の CHECK 制約
- ORM/Enum 定義
- 既存コード中の `error in (0,1)` 前提
- CSV出力/監視/メトリクス/集計ロジック

もし `error` が 0/1 の二値前提なら、ここで壊れます。

---

### 2) `confirmed=1` を「成功」とみなす既存処理への影響
今後は `confirmed=1, error=2` が「released」を意味します。  
したがって既存で

- `confirmed=1` を成功件数として数えている
- billing 対象を `confirmed=1` だけで拾っている
- archive 対象を `confirmed=1` だけで拾っている

といった処理があると誤集計します。

あなたの方針にある

> archive cron は confirmed=1 AND error IN (0,1) のみ対象、error=2 は別途 purge

はその対策として正しいです。  
ただし **archive cron 以外にも同様の参照がないか要確認**です。

---

### 3) 「claim_confirmed」の定義を実装で厳密化すべき
方針上は

- 完了状態 = `claim.confirmed != 0`

と読めますが、ここは実装でブレやすいです。  
`FinalizeState.claim_confirmed` は以下のように明記した方が安全です。

- `claim_confirmed := confirmed != 0`
- `claim_released := confirmed == 1 and error == 2` などは必要なら別途

少なくとも state loader 内の条件式が `confirmed == 1` で実装されると、今回の release marker 設計が崩れます。

---

## 結論として
**副作用は「あり得る」が、設計自体は採用可能**です。  
GO 条件は **`error=2` と `confirmed=1` の既存参照箇所点検**です。

---

# 3. 既存 23本のテスト(72ケース)を壊さないか?

## 結論
**そのままでは一部壊れる可能性が高い**です。  
ただし、それは悪い変更というより **仕様変更に伴う期待値更新**です。

---

## 壊れやすい箇所

### 1) finalize() の返り値型変更
これまでが `None` / `bool` / 単純値なら、呼び出し側テストは落ちます。  
既存テストで以下があれば修正必要です。

- `assert finalize(...) is None`
- `assert finalize(...) == True/False`
- 例外発生前提のテスト

---

### 2) transient finalize 後の claim 状態期待値
以前の DELETE 前提テストは落ちます。

- 「claim が消えている」期待
- 「再実行時に claim 不在 mismatch」期待
- archive の対象件数期待

ここは `confirmed=1, error=2` マーカー前提へ更新が必要です。

---

### 3) event_log 件数期待
mismatch ログの書き方を変えるので、イベント件数やタイミング期待値が変わる可能性があります。

---

### 4) allowed() stopped_budget 詳細文字列
`Decision.detail` や event detail の厳密一致テストがある場合、文言変更で落ちます。

---

## テスト追加案は妥当
挙げている 8 本はおおむね良いです。  
ただし **1本追加推奨**です。

### 推奨追加
- `test_finalize_state_mismatch_logs_persist_after_rollback_or_post_rollback_log.py`

理由:
今回の最大リスクがここだからです。  
**mismatch 返却だけでなく event_log が残ること**を必ず検証すべきです。

---

# 4. 本番反映急ぐ前提で、これでGO判定を出す条件は?

## 結論
**現時点では GO 不可。以下の必須条件を満たせば「十分・実装移行可」寄りです。**

---

## 必須条件（Blocking）

### 条件1: mismatch ログ永続化方式を修正
必須です。  
以下のどちらかを方針に反映してください。

- **推奨**: tx rollback 後に別 tx で `log_event()` 実行
- 代替: mismatch 時は更新を行わず `_log_event_in_tx` 後に commit

現行案の「tx内ログ → rollback」は不可です。

---

### 条件2: `claim_confirmed` 判定を実装仕様に明記
方針文に少なくとも以下を明記してください。

- transient released marker は `confirmed=1, error=2`
- `FinalizeState.claim_confirmed` は `confirmed != 0` で判定
- idempotent 判定もこの意味に従う

ここが曖昧だと実装者が `confirmed==1` なのか `!=0` なのかで揺れます。

---

### 条件3: `error=2` の影響調査完了
最低限 grep ベースでも良いので、以下の参照を洗ってください。

- `error == 0/1`
- `confirmed == 1`
- archive/billing/report/metrics

本番が明朝自動実行なら、ここは**机上レビューだけで流さない方がいい**です。

---

## 準必須に近い推奨

### 推奨1: FinalizeResult.detail に mismatch 理由を入れる
運用で追いやすくなります。

例:
- `reservation_missing`
- `claim_missing`
- `partial_finalized_reservation_only`
- `partial_finalized_claim_only`

---

### 推奨2: `_record_in_tx()` / `_release_in_tx()` の例外を finalize() で握りつぶさず status に正規化
運用上は `StateMismatchError` を `STATE_MISMATCH` に寄せた方が見やすいです。

---

### 推奨3: archive/purge の責務をコメントで固定
`error=2` の意味が後で忘れられやすいです。  
テーブル定義コメント or module comment に残すべきです。

---

# 質問ごとの端的回答

## 1. この強化版で前回指摘は完全解消するか?
**いいえ。ほぼ解消だが、`STATE_MISMATCH` の event_log が rollback で消える問題が未解消です。**

---

## 2. `DELETE → UPDATE(confirmed=1, error=2)` の副作用はないか?
**副作用候補はあるが、設計としては妥当です。**  
要確認は:

- `error=2` を許容できるか
- `confirmed=1` を成功扱いしている既存処理がないか
- archive 以外の下流処理への影響

---

## 3. 既存 23本のテスト(72ケース)を壊さないか?
**無修正では一部壊れる可能性が高いです。**  
主因は:

- finalize 戻り値型変更
- transient 後の claim 状態変更
- event/log detail 変更

ただし、これは仕様改善に伴う自然な影響です。

---

## 4. 本番反映急ぐ前提で、これでGO判定出すなら何が条件か?
**最低条件は3つです。**

1. mismatch ログ永続化方式を修正  
2. `claim_confirmed` の判定定義を明記  
3. `error=2` / `confirmed=1` 参照箇所の影響調査完了

---

必要なら次に、**「明朝8時までに通すための最小差分パッチ方針」**として  
「必須修正だけに絞った v2.10.2 短縮版」を私の方で起こせます。
