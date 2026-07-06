# 【Cursor作業指示】outreach_system v2 リファクタ
対象ディレクトリ: ses_work/outreach_system/
参照ファイル: SPEC.md / CLAUDE.md / この指示書
完了条件: 下記全タスク完了 + dry-run成功
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 背景
- 送信者名義が「松野」→「深谷 / 株式会社TERRA」に変更
- テンプレートが2種→3種に変更（統一・案件側・要員側）
- .envは更新済み（SENDER_NAME=深谷, SENDER_COMPANY=株式会社TERRA）
- メールアドレスは発行待ち。.envのOUTREACH_FROM_EMAILを差し替えるだけで切替可能にする

---

## Task 1: テンプレート3種をtemplates.pyに切り出し（新規作成）

`outreach_system/templates.py` を新規作成。
send_mail.py から SENDER_NAME, SENDER_COMPANY, OUTREACH_FROM_EMAIL を読み込んで使う。

```python
# templates.py

from send_mail import SENDER_NAME, SENDER_COMPANY, OUTREACH_FROM_EMAIL

def get_template(template_type: str, contact_name: str) -> tuple[str, str]:
    """
    Returns (subject, body) for the given template_type.
    template_type: "unified" | "project" | "engineer"
    """
    name = contact_name or "ご担当者"
    sender = SENDER_NAME or "深谷"
    company = SENDER_COMPANY or "株式会社TERRA"
    email = OUTREACH_FROM_EMAIL
    # ... テンプレート返却
```

### テンプレート定義（★松野が後で文面修正する前提のドラフト）

#### unified（統一版）
件名: 案件・人員の情報交換のご相談／{company}

```
{name}様

突然のご連絡失礼いたします。
{company} {sender}と申します。

弊社はSES事業を展開しており、
案件情報・人員情報の交換を積極的に行っております。

貴社にてエンジニアをお探しの際はご提案が可能ですし、
案件をお持ちの際はぜひご紹介いただければ幸いです。

まずは情報交換からでも構いませんので、
ご興味がございましたらお気軽にご返信ください。

何卒よろしくお願いいたします。

━━━━━━━━━━━━━━━━
{company}
{sender}
Email: {email}
━━━━━━━━━━━━━━━━
```

#### project（案件側向け＝エンジニア提案）
件名: エンジニアのご提案について／{company}

```
{name}様

突然のご連絡失礼いたします。
{company} {sender}と申します。

弊社はSESエンジニアのご提案を行っており、
貴社のエンジニアリソース確保のお力になれればと思い
ご連絡させていただきました。

■ ご提案可能なスキル帯
・Java / Python / PHP 等のWeb系開発
・AWS / Azure 等のインフラ・クラウド基盤
・PMO / 上流工程経験者

即日〜翌月稼働可能な人員を常時抱えております。
エンジニアをお探しの際は、お気軽にご返信いただければ幸いです。

何卒よろしくお願いいたします。

━━━━━━━━━━━━━━━━
{company}
{sender}
Email: {email}
━━━━━━━━━━━━━━━━
```

#### engineer（要員側向け＝案件紹介・BP提携）
件名: BP提携・案件情報のご相談／{company}

```
{name}様

突然のご連絡失礼いたします。
{company} {sender}と申します。

弊社はSES事業を展開しており、
常時複数の案件情報を保有しております。

貴社にてフリー予定のエンジニア様がいらっしゃいましたら、
ぜひご紹介いただければ幸いです。
案件内容に応じて柔軟にご提案させていただきます。

ご興味がございましたら、お気軽にご返信ください。

何卒よろしくお願いいたします。

━━━━━━━━━━━━━━━━
{company}
{sender}
Email: {email}
━━━━━━━━━━━━━━━━
```

---

## Task 2: outreach.py のテンプレート呼び出し修正

1. outreach.py から `build_template()` 関数を削除
2. 代わりに `from templates import get_template` を使う
3. targets.csv の `type` カラムの値とテンプレートの対応:

| type値 | テンプレート |
|---|---|
| 元請け | project |
| SES | engineer |
| (空 or その他) | unified |

4. テンプレート選択ロジック:
```python
TYPE_MAP = {"元請け": "project", "SES": "engineer"}
template_type = TYPE_MAP.get(target["type"], "unified")
subject, body = get_template(template_type, target["contact_name"])
```

---

## Task 3: send_mail.py に SENDER_COMPANY 追加

```python
SENDER_COMPANY = config.get("SENDER_COMPANY", "株式会社TERRA")
```
export に SENDER_COMPANY を追加。

---

## Task 4: targets.csv の type カラム仕様更新

targets.csv の type カラムに以下の値を許容:
- "元請け" → project テンプレート
- "SES" → engineer テンプレート
- "" (空) → unified テンプレート

既存データは全て "SES" なのでそのまま。

---

## Task 5: SPEC.md 更新

- テンプレートを3種（unified / project / engineer）に更新
- templates.py の構成を追記
- credentialロードに SENDER_COMPANY を追記

---

## Task 6: TERRAリスト取り込みスクリプト（import_terra_list.py）

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

取り込みルール:
- D列がメールアドレス形式（@含む）→ emailに設定
- D列がURL or 空 → emailは空（送信スキップ対象）
- type: デフォルトは空（unified）。スプレッドシートに元請け記載あれば「元請け」、SES記載あれば「SES」
- memo: 空

実行:
```bash
python outreach_system/import_terra_list.py --dry-run
python outreach_system/import_terra_list.py --run
```

---

## Task 7: dry-run 検証

全タスク完了後:
```bash
python outreach_system/outreach.py --dry-run
```

確認項目:
- テンプレート文面に「深谷」が含まれ「松野」が含まれない
- type="SES"の行にengineerテンプレートが適用される
- type="元請け"の行にprojectテンプレートが適用される
- type=""の行にunifiedテンプレートが適用される

---

## 禁止事項
- .envファイルは編集しない（ジョブズが更新済み）
- 本番送信（--run）は絶対に実行しない
- history.json をリセットしない
