import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

base = os.path.join(os.environ["USERPROFILE"], "OneDrive", "\u30c7\u30b9\u30af\u30c8\u30c3\u30d7", "ses_work")
pending = os.path.join(base, "pending_tasks")

task_k = """# 【Cursor作業指示】Task K: 全件取込モード移行（PROCESS_LIMIT引き上げ）

対象ディレクトリ: ses_work/mail_pipeline/
作業内容: PROCESS_LIMITを200に引き上げ、全メールを処理対象にする
完了条件: PROCESS_LIMIT=200 + CostGuardが$8/日で確実に止まることのテスト
質問がある場合: Claude.aiチャットに貼り付けて確認

**CEO承認済み。CostGuard v2 fail-close（Task C実装済み）が安全弁。**

---

## 修正1: PROCESS_LIMIT引き上げ

### 対象ファイル
mail_pipeline/mail_pipeline.py

### 変更
```python
# 変更前
PROCESS_LIMIT = 50

# 変更後
PROCESS_LIMIT = 200  # FETCH_LIMITと同値。全件処理。
```

### 安全確認
CostGuard v2のfail-closeにより:
- 日次$8超過 → 自動停止（翌日に残りを処理）
- 月次$140超過 → 自動停止

PROCESS_LIMIT=200 x 13回/日 = 最大2600件/日 → $8.32/日 → CostGuardが途中で止める
→ 実際には$8に達した時点で停止するため、暴走しない

## 修正2: バックログ消化の進捗ログ追加

main()の末尾に以下を追加:
```python
# 未処理件数をログ出力（バックログ消化の進捗確認用）
remaining = get_unprocessed_count()
log(f"残りバックログ: {remaining}件")
```

## テスト
- PROCESS_LIMIT=200が反映されていること
- CostGuardが$8/日で処理をブロックすること（モックテスト）
- バックログ件数がログに出力されること

---

## 共通ルール
- 既存テスト全パス / 新規コードにtype hint
"""

fpath = os.path.join(pending, "20260619_190400_taskK_full_process.md")
with open(fpath, 'w', encoding='utf-8') as f:
    f.write(task_k)
print(f"saved: taskK")

print("\n--- pending_tasks/ 一覧 ---")
for f in sorted(os.listdir(pending)):
    if f.startswith('2026'):
        size = os.path.getsize(os.path.join(pending, f))
        print(f"  {f} ({size:,} bytes)")
