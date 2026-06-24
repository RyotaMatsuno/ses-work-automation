# 【Cursor作業指示】Task BD: CostGuardテストモード実装

対象ファイル: ses_work/common/ledger.py + ses_work/tests/test_costguard_integration.py（新規）
作業内容: CostGuardのブロック動作を自動検証できるテストモードを実装
参照ファイル: CLAUDE.md / common/ledger.py / common/state_store.py
完了条件: pytest実行でCALL_LIMIT/USD上限/pending_queue投入が自動検証される
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 背景（GPT-5.4壁打ち合意済み）
- CostGuardは「実装されている」ではなく「確実に意図通り止まる」を保証する必要がある
- 現在は手動確認のみ。上限変更時にリグレッションが起きても検知できない

## 変更内容

### 1. テスト用環境変数
```
COSTGUARD_TEST_MODE=true
TEST_DAILY_LIMIT_USD=0.10
TEST_MONTHLY_LIMIT_USD=0.50
TEST_CALL_LIMIT_MATCHING_BATCH=3
TEST_CALL_LIMIT_MATCHING_PIPELINE=3
TEST_CALL_LIMIT_CLASSIFY=5
```

### 2. ledger.py修正
- `_call_limit()` 内で `COSTGUARD_TEST_MODE=true` の場合はTEST_*値を優先
- `_usd_limit()` 内も同様
- テストモードではstate.sqlite3とは別のテスト用DBを使用（`:memory:` or tmpfile）

### 3. テストケース（tests/test_costguard_integration.py 新規作成）

#### レベル1: ユニットテスト
- test_call_limit_blocks_at_threshold: CALL_LIMIT=3で4回目がブロック
- test_call_limit_pending_queue: ブロック時にpending_queueに投入される
- test_usd_daily_blocks: 日次$0.10で超過時ブロック
- test_usd_monthly_blocks: 月次$0.50で超過時ブロック

#### レベル2: 統合テスト
- test_matching_batch_pipeline_isolation: batch上限到達でもpipelineはブロックされない
- test_pending_queue_fifo: キュー投入順にFIFO処理される
- test_pending_expire: 7日経過でstatus=expired

#### レベル3: フェーズ分離テスト（Task BA完了後）
- test_phase_separation: matching_batchとmatching_pipelineが独立動作

### 4. CI用実行コマンド
```
COSTGUARD_TEST_MODE=true python -m pytest tests/test_costguard_integration.py -v
```

## 注意事項
- テストモードは本番DBに一切触れない設計
- テスト終了後に一時DBは自動削除
- fail-close原則: テストモード判定に失敗した場合は本番制限値を使用
