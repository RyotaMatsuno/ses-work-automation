# ゲート① レビュー結果(SPEC v2.2)

レビュー日時: 2026-06-16T18:19:09.679949
モデル: gpt-5.4 (reasoning_effort=low, max_completion_tokens=8000)
usage: {"prompt_tokens": 3773, "completion_tokens": 2707, "total_tokens": 6480, "prompt_tokens_details": {"cached_tokens": 0, "audio_tokens": 0}, "completion_tokens_details": {"reasoning_tokens": 888, "audio_tokens": 0, "accepted_prediction_tokens": 0, "rejected_prediction_tokens": 0}}

---

【条件付きGO】

### 修正必須項目
- **装置3(重複起票防止)と装置1(DAILY_CALL_LIMIT)の実行順序を明記してください。**
  - 現状仕様では、`check_daily_limit()` を「API呼び出し前に先行判定」としか書いておらず、**重複スキップ判定より前に日次回数判定/加算される実装**になり得ます。
  - §5.2 では「重複時は完全スキップ(counter追記しない)」とあるため、**dedup判定が先**でないと整合しません。
  - 少なくとも全体順序を  
    `dedup判定 → phase/model決定 → 単発閾値判定 → is_allowed(check_daily_limit → can_spend) → 実呼び出し → 実績記録`  
    のように固定化してください。

- **DAILY_CALL_LIMIT のカウント更新タイミングを明記してください。**
  - 「31回目が exit 1」とある一方、**30回目をどの時点で加算するか**が不明です。
  - `check_daily_limit()` が事前判定だけなのか、予約(in-flight)を取るのか、成功時のみ加算なのかで挙動が変わります。
  - 仕様未確定のままだと、**失敗した呼び出しも回数消費する／しないの差異**や、実装ごとの差が出ます。

- **ledger / dedup_state の更新を排他制御前提で定義してください。**
  - `ledger.py` と `dedup_state.json` をファイルベースで運用するなら、**複数プロセス同時実行時に race condition** が起きます。
  - 具体的には:
    - 2プロセスが同時に `check_daily_limit()` を通って **日次回数超過**を防げない
    - 2プロセスが同じ `dedup_key` を同時に見て **重複起票防止が破れる**
  - 2026-06-02 のような暴走防止が目的なら、ここは仕様として未定義のままにできません。  
    **ファイルロック / sqlite / atomic rename** のいずれかを必須化してください。

- **exit code 2 の意味を「エラー」と「意図的スキップ」で同居させないでください。**
  - §9.1 では `exit 2 = エラー/スキップ`、しかも「呼び出し側はリトライまたはスキップ」となっており、**運用判断が分岐できません**。
  - 例:
    - `models.list()` 一時失敗 → 本来はリトライ候補
    - dedup重複 → リトライ不要
    - fallback先全不在 → 環境依存で要通知/要調査
  - 少なくとも **終了コードは同じでも reason を機械判定可能に返す仕様**を必須化してください。  
    例: `error_transient / skipped_duplicate / skipped_model_unavailable` など。

- **`is_allowed()` の責務範囲と装置2の判定位置を明記してください。**
  - §6.1 の `is_allowed()` は `check_daily_limit()` と `can_spend()` しか見ておらず、**装置2のフェーズ別単発閾値判定がどこで実行されるか不明**です。
  - その結果、呼び出し側によって
    - 装置2を先に見る実装
    - ledgerだけ呼ぶ実装
    - 両方呼ぶ実装
    が混在し得ます。
  - 既存呼び出し側互換性を担保するには、**共通の単一エントリポイント**を定義するか、少なくとも**判定順序を仕様として一本化**してください。

- **装置3の `dedup_key = {date}:{block_type}:{phase}` は粒度が粗すぎるため、正当な別件起票を潰すリスクがあります。**
  - 同一日・同一 `block_type`・同一 `phase` で、**原因や対象データが異なる事象**まで同一視されます。
  - 例: 同じ `gate_check:design` でも、別案件・別入力・別失敗理由の起票がすべて1件に潰れる可能性があります。
  - `block_type` に原因分類が必ず含まれる前提がない限り、**`reason` / `source` / `target_id` 等を含めた粒度再設計**が必要です。

- **`models.list()` 失敗時の扱いを「安全側停止」として運用要件まで落とし込んでください。**
  - 現仕様は `available_models = set()` にして fallback 経路へ進めるため、実質 **全phaseで最終的に exit 2** になります。
  - コスト安全性の観点では妥当ですが、業務上は **一時的なモデル一覧取得失敗で全ジョブ停止** です。
  - 仕様として
    - 何回まで即時リトライするか
    - どの reason で exit 2 にするか
    - LINE通知対象か
    を決めないと、現場では「安全だが止まりすぎる」運用になります。

- **通知優先順位と停止理由の対応表を追加してください。**
  - §8 に優先順位はありますが、**どの reason がどの通知カテゴリに対応するか**が未定義です。
  - 特に `exit 2` 系:
    - duplicate skip
    - models.list failure
    - fallback先全不在
    - その他内部エラー
    で通知有無が変わるはずですが、現仕様ではぶれます。
  - **reason → 通知レベル → exit code** の対応表を1つに統一してください。

### 推奨項目
- **`AppData/Local/...` 固定パスはOS依存なので、設定化を推奨します。**
  - Windows前提でなければ、将来 Linux 実行環境で詰まります。

- **未知モデルの fallback rate を `gpt-4o` 固定にする妥当性の注記を推奨します。**
  - 実際には `codex-5` や将来高額モデルが未知扱いになると、**過小見積もり**になる可能性があります。
  - 安全側に倒すなら「未知モデルはより高い保守的レート」を検討余地ありです。

- **テスト計画に並行実行系を追加することを推奨します。**
  - `test_call_limit_race`
  - `test_dedup_race`
  - `test_models_list_failure_exit2_reason`
  - `test_duplicate_does_not_consume_daily_call`
  は最低限あると安心です。

- **`matching_v2/skill_judge.py` の既知バグが背景にあるため、v2/v3 混在検出チェックを推奨します。**
  - せっかく仕様を固めても、旧呼び出し経路が残ると事故再発余地があります。

- **`estimate_cause()` の入出力例を追加すると保守しやすいです。**
  - どの超過でどの文字列を返すか、優先順位があるかを例示すると実装差異を減らせます。
