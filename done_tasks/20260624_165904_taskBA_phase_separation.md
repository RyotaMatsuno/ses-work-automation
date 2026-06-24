# 【Cursor作業指示】Task BA: CostGuard matching phase分離

対象ディレクトリ: ses_work/common/ + ses_work/matching_v3/ + ses_work/mail_pipeline/ + ses_work/config/
作業内容: matching CALL_LIMITを用途別に分離し、バッチとパイプラインの予算競合を解消
参照ファイル: CLAUDE.md / common/ledger.py / matching_v3/matching_v3.py / mail_pipeline/mail_pipeline.py
完了条件: matching_batchとmatching_pipelineが独立した予算枠で動作
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 背景
- matching_v3（朝8時バッチ）とmail_pipeline内のai_matching（提案文生成）が同じ`matching`フェーズ予算(上限60)を共有
- バッチが30消費→パイプラインが枯渇するパターンが頻発（1日79件ブロック実績）
- GPT-5.4壁打ちで「異なる目的の処理が同じ予算を奪い合っている」のが本質と合意

## 変更内容

### 1. config/.env に新フェーズ追加
```
# 旧: DAILY_CALL_LIMIT_MATCHING=60
# 新:
DAILY_CALL_LIMIT_MATCHING_BATCH=40
DAILY_CALL_LIMIT_MATCHING_PIPELINE=30
```
※旧DAILY_CALL_LIMIT_MATCHINGは残してフォールバックに使用

### 2. common/ledger.py の _call_limit() 修正
- `matching_batch` / `matching_pipeline` をphaseとして認識
- envから `DAILY_CALL_LIMIT_MATCHING_BATCH` / `DAILY_CALL_LIMIT_MATCHING_PIPELINE` を読む
- 未定義の場合は `DAILY_CALL_LIMIT_MATCHING` にフォールバック

### 3. matching_v3/matching_v3.py
- CostGuard呼び出しの `phase="matching"` → `phase="matching_batch"` に変更
- 全箇所を確認（cost_guard.pyのreserve呼び出し含む）

### 4. mail_pipeline/mail_pipeline.py
- `call_claude(..., phase="matching")` → `phase="matching_pipeline"` に変更
- line 1169: ai_matching関数内の呼び出し
- pending_queue関連もphase名を更新

### 5. event_log / pending_queue の後方互換
- 既存の `phase="matching"` レコードはそのまま残す
- 新しいレコードから新phase名を使用

## テスト
1. matching_v3 dry-run → phase_callsに `matching_batch` が記録される
2. mail_pipeline実行 → phase_callsに `matching_pipeline` が記録される
3. matching_batch上限到達 → matching_pipelineはブロックされない
4. 既存テスト全PASS

## 注意事項
- CostGuardのfail-close原則を維持（envが壊れたらブロック方向に倒す）
- state.sqlite3のphase_callsテーブルのスキーマ変更は不要（phaseはTEXT型）

---

## 完了メモ (2026-06-24)
- `config/.env`: `DAILY_CALL_LIMIT_MATCHING_BATCH=40`, `DAILY_CALL_LIMIT_MATCHING_PIPELINE=30` 追加
- `common/ledger.py`: `_call_limit()` に matching_batch/pipeline → MATCHING フォールバック
- `matching_v3/matching_cost_guard.py`: `matching_batch` phase で `allowed()/finalize()` 連携（旧 cost_guard.py をリネーム）
- `matching_v3.py` / `structurer.py` / `realtime_match_worker.py`: matching_batch + pending_queue 更新
- `mail_pipeline.py`: `ai_matching` → `phase="matching_pipeline"`
- `tests/test_task_ba_phase_separation.py` 6件パス
