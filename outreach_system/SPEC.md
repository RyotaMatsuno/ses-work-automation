# SPEC.md — アポ取りシステム（outreach_system）

最終更新: 2026-07-03

## 目的
元請け・SES企業の担当者リストに対して、テンプレートメールを一括送信し、
新規アポイントメントを自動取得する。
再送制御（180日）と断り除外で精度を上げる。

## データ構成（3層構造）

```
master_companies.csv     ← TERRA原本（26,430社）
  ↓ filter_it_ses.py
qualified_companies.csv  ← SES/IT企業のみ（industry_status付き）
  ↓ enrich_emails.py
targets.csv              ← メアドあり or フォームURLあり = 送信可能企業
  ↓ outreach.py
result_outreach.json     ← 送信結果
```

## システム構成
```
outreach.py（メイン送信）
  ├─ master_companies.csv      ← TERRA全件リスト
  ├─ qualified_companies.csv   ← SES/ITフィルタ済み
  ├─ targets.csv               ← 送信先リスト
  ├─ history.json              ← 送信履歴（再送制御用）
  ├─ enrich_state.json         ← HP巡回処理状態
  ├─ send_mail.py              ← SMTP送信・送信者情報
  ├─ templates.py              ← テンプレート定義（3種）
  ├─ import_terra_list.py      ← TERRAリスト取り込み
  ├─ filter_it_ses.py          ← SES/IT業種フィルタ
  ├─ enrich_emails.py          ← HP巡回メアド取得
  └─ result_outreach.json      ← 送信結果ログ
```

## master_companies.csv / qualified_companies.csv 形式
```csv
company,contact_name,email,type,memo
株式会社サンプル,,,,メモ
```
qualified_companies.csv には `industry_status` 列を追加（include / review）。

## 送信先リスト（targets.csv）形式
```csv
company,contact_name,email,type,memo
株式会社サンプル,田中,tanaka@example.com,元請け,
株式会社テスト,,,form_url:https://example.com/contact
```
- type: 「元請け」→ project / 「SES」→ engineer / 空・その他 → unified
- memo: 「断り」が含まれる行は自動除外
- memo の `form_url:` は enrich で取得した問い合わせフォーム（将来対応）

## filter_it_ses.py

master_companies.csv から SES/IT 企業を判定。

| industry_status | 意味 |
|---|---|
| include | 肯定キーワード一致 → qualified に出力 |
| review | キーワード不一致 → qualified に出力（手動確認用） |
| exclude | 否定キーワード一致 → 除外 |

```bash
python filter_it_ses.py --dry-run
python filter_it_ses.py --run
```

出力: `qualified_companies.csv`, `filter_report.json`

## enrich_emails.py

qualified_companies.csv のメアドなし企業について HP からメアド/フォームURLを取得。

### HP特定（優先順）
1. memo 列の URL
2. Google 検索「{企業名} 公式」（requests + BeautifulSoup）
3. Bing RSS 検索（Google が JS/CAPTCHA で失敗した場合のフォールバック）

### 巡回対象
トップ + `/contact`, `/inquiry`, `/お問い合わせ`, `/company`, `/about`, `/会社概要`, `/recruit`, `/採用`

### レート制限
- HP巡回: 3秒/ページ
- Google検索: 20秒/クエリ
- robots.txt disallow 時はスキップ

### シャード並列
```bash
python enrich_emails.py --shard-id 0 --shard-count 5 --limit 200 --dry-run
python enrich_emails.py --shard-id 0 --shard-count 5 --limit 200 --run
python enrich_emails.py --export-to-targets
```

出力: `enrich_state.json`, `enrich_report.json`

## import_terra_list.py

```bash
python import_terra_list.py --target master --dry-run   # 全件 → master_companies.csv
python import_terra_list.py --target targets --dry-run  # メアドあり → targets.csv（デフォルト）
python import_terra_list.py --run                       # デフォルト targets
```

## テンプレート定義（templates.py）

テンプレートは3種。`get_template(template_type, contact_name) -> (subject, body)` で取得。

### unified（統一版 / typeが空・その他）
件名: `案件・人員の情報交換のご相談／{company}`

### project（元請け向け＝エンジニア提案 / type="元請け"）
件名: `エンジニアのご提案について／{company}`

### engineer（要員側向け＝BP提携・案件紹介 / type="SES"）
件名: `BP提携・案件情報のご相談／{company}`

送信者情報（`{sender}`・`{company}`・`{email}`）は .env の SENDER_NAME / SENDER_COMPANY / OUTREACH_FROM_EMAIL から自動取得。

## 再送制御ルール
- history.jsonに送信日時を記録
- 前回送信から180日（半年）未満は送信しない
- 初回送信は無条件でOK

## 除外ルール
- targets.csvのmemoに「断り」が含まれる → 除外
- メールアドレスがない → 除外（フォームURLは enrich で memo に記録、送信は将来実装）

## SMTP設定
- 送信元: FP新営業アドレス（.envの OUTREACH_FROM_EMAIL）
- CC: r-matsuno@terra-ltd.co.jp
- SMTPホスト: mail65.onamae.ne.jp:465 SSL
- パスワード: .envの OUTREACH_MAIL_PASSWORD

## dry_run引数
```bash
python outreach.py --dry-run    # 送信なし・ログのみ（デフォルト）
python outreach.py --run        # 本番送信（要確認）
```

## credentialロード
```python
from dotenv import dotenv_values
ENV_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env"
config = dotenv_values(ENV_PATH)
OUTREACH_FROM_EMAIL = config.get("OUTREACH_FROM_EMAIL", "r-matsuno@terra-ltd.co.jp")
OUTREACH_MAIL_PASSWORD = config.get("OUTREACH_MAIL_PASSWORD", config.get("SESSALES_MAIL_PASSWORD", ""))
SENDER_NAME = config.get("SENDER_NAME", "")
SENDER_COMPANY = config.get("SENDER_COMPANY", "株式会社TERRA")
MATSUNO_EMAIL = "r-matsuno@terra-ltd.co.jp"
```

## 注意
- OUTREACH_FROM_EMAILとOUTREACH_MAIL_PASSWORDが.envに未設定の場合は
  松野アドレス（r-matsuno@terra-ltd.co.jp）とSESSALES_MAIL_PASSWORDでフォールバック
- master_companies.csv / targets.csv の既存データは削除しない（追記のみ）
- LLM API は使用しない（ルールベースのみ）
