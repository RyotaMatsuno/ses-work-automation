# 【Cursor作業指示】Task BE: Batch APIハング再発防止（lock TTL + timeout）

対象ファイル: ses_work/mail_pipeline/mail_pipeline.py
作業内容: パイプラインのBatch API応答待ちハングを防止
参照ファイル: CLAUDE.md
完了条件: Batch APIタイムアウト・lock TTL・stuck recovery実装
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 背景
- 2026-06-24 15:00にBatch API送信後81分間ロック状態でパイプライン停止
- 288件が未分類のまま滞留
- lock解除で復旧したが再発リスクあり

## 変更内容

### 1. pipeline.lockにTTL（45分）
```python
LOCK_TTL_MINUTES = 45

def acquire_lock():
    lock_path = LOCK_FILE
    if os.path.exists(lock_path):
        age_minutes = (time.time() - os.path.getmtime(lock_path)) / 60
        if age_minutes > LOCK_TTL_MINUTES:
            log(f"[LOCK] stale lock detected ({age_minutes:.0f}min). Force removing.")
            os.remove(lock_path)
        else:
            raise RuntimeError(f"Pipeline locked ({age_minutes:.0f}min ago)")
    # 通常のlock取得
    ...
```

### 2. Batch API応答のタイムアウト（20分）
```python
BATCH_POLL_TIMEOUT_MINUTES = 20

def wait_for_batch(batch_id):
    start = time.time()
    while True:
        elapsed = (time.time() - start) / 60
        if elapsed > BATCH_POLL_TIMEOUT_MINUTES:
            log(f"[BATCH] timeout after {elapsed:.0f}min. Batch {batch_id} abandoned.")
            return None  # タイムアウト→次回再処理
        status = check_batch_status(batch_id)
        if status == "completed":
            return fetch_batch_results(batch_id)
        time.sleep(10)
```

### 3. stuck recovery
- タイムアウトしたBatchのメールはclassify_result=Nullのまま残る
- 次回パイプライン実行時にpending_queueから自動再処理される（既存仕組み）

### 4. ログ強化
- Batch送信時: `[BATCH] submitted {batch_id} ({n}件) at {time}`
- ポーリング中: `[BATCH] polling {batch_id} ({elapsed}min elapsed)`
- タイムアウト: `[BATCH] TIMEOUT {batch_id} after {elapsed}min`

## テスト
1. lock TTL: 45分超のlockファイルが自動解除される
2. Batch timeout: 20分超でタイムアウトし、処理が継続する
3. タイムアウト後のメールが次回実行で再分類される
4. 既存テスト全PASS
