# CLAUDE.md - cost_guard_v2 作業ルール

最終更新: 2026-06-16 / バージョン: v2.10

---

## 0. プロジェクト概要

cost_guard 拡張(装置1〜3 + DAILY_CALL_LIMIT + 並行制御 + claim方式)の3点セット保持ディレクトリ。

- **本ディレクトリの責務**: SPEC/TASKS/CLAUDE の保持のみ
- **コード実装ターゲット**:
  - `ses_work/common/ledger.py` (改修・sqlite移行)
  - `ses_work/common/state_store.py` (新規)
  - `ses_work/common/model_selector.py` (新規)
  - `ses_work/common/dedup.py` (新規・claim方式)
  - `ses_work/common/notifier.py` (新規)
  - `ses_work/common/exit_handler.py` (新規)
  - `ses_work/cost_guard.py` (改修・統一エントリ allowed/finalize)
  - `ses_work/migrations/migrate_to_sqlite_v2.4.py` (新規・一回実行)
  - `ses_work/config/dedup_target_required.json` (新規)

## 1. 必須遵守事項

1. 3点セットを必ず最新と一致
2. **CostGuardなしのLLM呼び出し禁止**: 全LLM経路で `cost_guard.allowed()` を通す。呼び出し後は `finalize()` を try/finally で必ず呼ぶ
3. 文字エンコーディング UTF-8固定: `common/io_utils.py` の `setup_stdout()` を使う
4. 日本語パス禁止: cwd/コマンドに直接渡さない
5. exit code 規約:
   - 0 = GO / 1 = 明確な停止 / 2 = スキップ/エラー
   - reason は `Decision.reason` で機械判定(13値 enum)

## 2. 禁止事項

- §6 統一実行順序の逆順実装
- 装置3 重複時の counter 追記(完全スキップ + claim方式で統一)
- 装置3を「事後 mark」方式で実装(**必ず claim_dedup で事前 INSERT**)
- 装置2 閾値のハードコード
- 装置1 モデル一覧のハードコード
- DAILY_CALL_LIMIT を成功時加算で実装(事前予約方式で統一)
- sqlite を使わずファイルロックで代用
- `cost_state.json` への直接書き込み(sqlite 経由のみ)
- `check_daily_limit()` を本番判定に使うこと(reserve を使うこと、これは監視専用)
- `models.list()` 全失敗時に fallback を試みる旧実装(中断して error_transient_models_list を返す)
- finalize() の呼び忘れ(try/finally で保証)
- record() / release() で `reserved -= 1` を忘れる(SPEC §3.2.1)
- finalize() を success=False かつ error_kind="" のような不正組み合わせで呼ぶ(raise ValueError で拒否、assert は `python -O` で消えるので使わない)
- `ledger.record()` を `script=""` で呼ぶ(Decision.script を必ず伝搬すること)
- finalize() で record/release/confirm_dedup/release_dedup を**別々のトランザクション**で実行する(中途破綻リスク、単一 BEGIN IMMEDIATE 必須、SPEC §3.2.2)

## 3. 変更フロー

```
仕様変更 → SPEC.md 更新(章番号明記) → TASKS.md 更新 → 実装 → pytest → ゲート② → デプロイ
```

## 4. テスト要件

- 装置1〜3 各機能テスト
- **並行系**: test_call_limit_race / test_dedup_claim_race
- **claim方式**: test_dedup_claim / test_dedup_claim_transient_release / test_dedup_ttl_expiry
- **予約方式**: test_reservation_rollback / test_duplicate_does_not_consume_daily_call
- **必須マップ**: test_target_id_required_violation
- **permanent分岐**: test_finalize_permanent_kinds
- **互換**: test_v2_v3_no_mixed_call / test_exit_code2

## 5. ゲート暫定運用

- gate_checker は本体バグ未修正のため使わない
- 暫定: 素 OpenAI API + gpt-5.4 + reasoning_effort=low + max_completion_tokens=8000

## 6. 既存資産との関係

| 既存パス | 状態 |
|---|---|
| `cost_control/` | 2026-06-05 凍結(冒頭バナー追記済み) |
| `pf1_costguard/` | 2026-06-05 凍結(冒頭バナー追記済み) |
| `common/ledger.py` | 改修対象 |
| `cost_guard.py` | 改修対象 |
| `cost_state.json` | 移行後 `.bak_v2.4` に rename(readonly backup) |

## 7. コスト制約

- ledger ハード: $8/日
- CostGuard ソフト: $140/月
- Emergency: $300/月
- 装置2 フェーズ別単発閾値: 軽 $0.025 / 中 $0.10 / 重 $0.15
- DAILY_CALL_LIMIT: 初期30
- claim TTL: 初期 3600秒

## 8. reason enum(14値、SPEC §9)

`ok / skipped_duplicate / stopped_budget / stopped_call_limit / stopped_phase_threshold / error_transient_models_list / error_transient_api / error_model_unavailable_all_fallback / error_permanent_api / error_auth / error_bad_request / error_response_invalid / **error_missing_target_id** / error_internal`

## 9. 行き詰まり時

- 同じエラーで2回失敗 → `wall_hitting.py --problem`
- 仕様判断不能 → Claude.ai ジョブズに質問
- 費用発生・岡本連絡・根本設計変更 → 必ず松野確認

## 変更履歴

| 日付 | バージョン | 内容 |
|---|---|---|
| 2026-06-16 | v2.2 | 初版 |
| 2026-06-16 | v2.3 | 統一エントリ allowed/finalize / sqlite並行制御 / Decision dataclass / reason enum |
| 2026-06-16 | v2.4 | claim方式 / reason enum 13値 / models.list 中断統一 / target_id 必須マップ |
| 2026-06-16 | v2.5 | error_missing_target_id 新設(14値) / TTL inline purge / finalize 冪等性 |
| 2026-06-16 | v2.6 | (SPEC のみ更新) |
| 2026-06-16 | v2.7 | gate①五反映: §14 矛盾テスト削除 / §5.3 言い回し / §7.1 docstring強化 / §9 detail値例 |
| 2026-06-16 | v2.8 | gate①六反映: §3.2.1 reserved 減算明記 / §7.1 失敗時Decision既定値・model_hint・finalize不正引数 / §7.3 新設 / §8.2 event_log追加 / §11.3 log_event新規 / §14 テスト4本追加 |
| 2026-06-16 | v2.9 | gate①七反映: Decision.detail/script 追加 / allowed script 伝搬 / finalize 不正引数 raise化 / log_event タイミング表 / §14 テスト2本追加 |
| 2026-06-16 | v2.10 | gate①八反映: §3.2.2 finalize 原子性(単一 BEGIN IMMEDIATE) / Decision.phase/block_type / event_log script列 / log_event script引数 / finalize_state_mismatch / 8.19 ValueError修正 / 8.23 atomicity テスト |
