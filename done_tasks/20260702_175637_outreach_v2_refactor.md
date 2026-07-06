# 【Cursor作業指示】outreach_system v2 リファクタ
対象ディレクトリ: ses_work/outreach_system/
参照ファイル: SPEC.md / CLAUDE.md / この指示書
完了条件: 下記全タスク完了 + dry-run成功
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 背景
- アポ取りシステムの送信者名義が変更になった
- 旧: 松野（r-matsuno@terra-ltd.co.jp）
- 新: 深谷 / 株式会社TERRA / メアド発行待ち（.envで切替可能）
- テンプレート内に「松野」が3箇所ハードコードされているので変数化が必要
- TERRAの既存リスト（~150社）のtargets.csv取り込みも未実施

## タスク一覧

### Task 1: テンプレートのハードコード除去（outreach.py）

`build_template()` 関数内の以下3箇所を修正:

1. `sender_name_with_family = f"松野 {SENDER_NAME}".rstrip()`
   → `sender_name = SENDER_NAME or "深谷"` に変更（松野を削除）

2. テンプレートA本文: `お世話になっております。株式会社TERRA 松野と申します。`
   → `お世話になっております。{sender_company} {sender_name}と申します。`

3. テンプレートB本文: 同上の修正

4. テンプレートA署名: `松野 {SENDER_NAME}` → `{sender_name}` のみ

5. send_mail.py に SENDER_COMPANY の読み込みを追加:
   ```python
   SENDER_COMPANY = config.get("SENDER_COMPANY", "株式会社TERRA")
   ```
   outreach.py の import に SENDER_COMPANY を追加

6. テンプレートA/B の署名の会社名も変数化:
   ```
   {sender_company}
   {sender_name}
   {OUTREACH_FROM_EMAIL}
   ```

### Task 2: SPEC.md 更新

SPEC.mdのテンプレートA/Bのサンプル文面を、変数化後の内容に更新。
credentialロードセクションに SENDER_COMPANY を追加。

### Task 3: TERRAリスト取り込みスクリプト（import_terra_list.py）

新規ファイル `outreach_system/import_terra_list.py` を作成。

機能:
- Google Sheets API でスプレッドシート（ID: 1LootFV_qe4ZepuRBPBNLaNgjxqqkVj2QJEcGvU8CSBg）を読み込む
- 各行から会社名・担当者名・メールアドレス・種別・メモを抽出
- targets.csv に追記（既存会社名と重複する行はスキップ）
- 取り込み結果をprint出力

認証:
```python
from google.oauth2.service_account import Credentials
import gspread

CREDS_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\google_credentials.json"
SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPES)
gc = gspread.authorize(creds)
ss = gc.open_by_key("1LootFV_qe4ZepuRBPBNLaNgjxqqkVj2QJEcGvU8CSBg")
```

スプレッドシートの列構成（事前確認済み）:
- A列: 会社名
- B列: 住所（不要）
- C列: 電話（不要）
- D列: メール or 問い合わせURL
- E列以降: 送信履歴等

取り込みルール:
- D列がメールアドレス形式（@含む）→ emailに設定
- D列がURL or 空 → emailは空（送信スキップ対象）
- type: デフォルトは「SES」。スプレッドシート上に「元請け」の記載があれば「元請け」
- memo: 空

実行:
```bash
python outreach_system/import_terra_list.py --dry-run  # 取り込みプレビュー
python outreach_system/import_terra_list.py --run       # 本番取り込み
```

### Task 4: dry-run 検証

全タスク完了後に以下を実行して動作確認:
```bash
python outreach_system/outreach.py --dry-run
```

出力に以下が含まれることを確認:
- from= に .env の OUTREACH_FROM_EMAIL が表示される
- テンプレート文面に「深谷」が含まれ、「松野」が含まれない
- 送信対象リストが表示される

---

## 禁止事項
- .envファイルは編集しない（既にジョブズが更新済み）
- 本番送信（--run）は絶対に実行しない
- history.json をリセットしない
