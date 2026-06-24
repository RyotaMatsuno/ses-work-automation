import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

# 既存のTASKS.mdがあれば読む、なければ新規作成
tasks_path = "project_files/TASKS.md"

freee_tasks = """
## freee API連携・請求書自動化（優先度: 低）
追加日: 2026-05-12

### Phase 1: 調査・認証設定
- [ ] freee API仕様確認（OAuth2.0フロー・エンドポイント）
- [ ] freee開発者アカウント・アプリ登録（松野が実施）
- [ ] OAuth認証フロー実装（アクセストークン取得・リフレッシュ）
- [ ] 接続テスト（会社情報取得API）

### Phase 2: 請求書自動生成
- [ ] 請求書テンプレート設計（Notion案件DBから情報取得）
- [ ] freee請求書作成API実装
- [ ] 取引先マスタ連携（freee ↔ Notion）
- [ ] 請求書PDF生成・確認フロー

### Phase 3: 送付・入金確認自動化
- [ ] 請求書メール送付自動化（ses-mail連携）
- [ ] 入金確認APIポーリング実装
- [ ] 入金確認通知（LINE or メール）
- [ ] 月次レポート自動生成

### 前提条件
- freee有料プランが必要（スタータープラン以上）
- API利用には freee開発者登録が必要（松野が手動対応）
"""

if os.path.exists(tasks_path):
    with open(tasks_path, "r", encoding="utf-8") as f:
        existing = f.read()
    with open(tasks_path, "w", encoding="utf-8") as f:
        f.write(existing + "\n---\n" + freee_tasks)
    print("既存TASKS.mdにfreeeタスクを追記しました")
else:
    with open(tasks_path, "w", encoding="utf-8") as f:
        f.write("# TASKS.md\n\n" + freee_tasks)
    print("TASKS.md新規作成（freeeタスク追加済み）")

print(f"パス: {tasks_path}")
