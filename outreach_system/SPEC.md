# SPEC.md — アポ取りシステム（outreach_system）

最終更新: 2026-05-25

## 目的
元請け・SES企業の担当者リストに対して、テンプレートメールを一括送信し、
新規アポイントメントを自動取得する。
再送制御（180日）と断り除外で精度を上げる。

## システム構成
```
outreach.py（メイン）
  ├─ targets.csv     ← 送信先リスト（手動作成 or 自動取り込み）
  ├─ history.json    ← 送信履歴（再送制御用）
  ├─ send_mail.py    ← SMTP送信
  └─ result_outreach.json ← 送信結果ログ
```

## 送信先リスト（targets.csv）形式
```csv
company,contact_name,email,type,memo
株式会社サンプル,田中,tanaka@example.com,元請け,
株式会社テスト,鈴木,suzuki@test.co.jp,SES,断り2026-03
```
- type: 「元請け」「SES」のいずれか → テンプレートA/B切替
- memo: 「断り」が含まれる行は自動除外

## テンプレートA（元請け向け）
```
件名: エンジニアリングリソースのご提案

{contact_name}様

お世話になっております。株式会社TERRA 松野と申します。

SESエンジニアのご提案にてご連絡させていただきました。
Java/Python/インフラ等、幅広いスキルセットのエンジニアを
即日〜ご提案可能です。

ご興味がございましたら、お気軽にご返信ください。

株式会社TERRA
松野 {SENDER_NAME}
{SENDER_EMAIL}
```

## テンプレートB（SES向け）
```
件名: エンジニア情報交換・BP提携のご相談

{contact_name}様

お世話になっております。株式会社TERRA 松野と申します。

弊社はSES事業を展開しており、BP様との情報交換・相互提案を
積極的に進めております。

案件・人員情報の交換等、ご興味がございましたら
ぜひお気軽にご返信ください。

株式会社TERRA
{SENDER_NAME}
{SENDER_EMAIL}
```

## 再送制御ルール
- history.jsonに送信日時を記録
- 前回送信から180日（半年）未満は送信しない
- 初回送信は無条件でOK

## 除外ルール
- targets.csvのmemoに「断り」が含まれる → 除外
- メールアドレスがない → 除外（フォーム送信は将来実装）

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

## 出力（result_outreach.json）
```json
{
  "run_at": "2026-05-25T09:00:00",
  "dry_run": true,
  "total": 10,
  "sent": 8,
  "skipped": 2,
  "details": [
    {"company": "...", "email": "...", "status": "sent", "template": "A"},
    {"company": "...", "email": "...", "status": "skip_断り", "template": null}
  ]
}
```

## credentialロード
```python
from dotenv import dotenv_values
ENV_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env"
config = dotenv_values(ENV_PATH)
OUTREACH_FROM_EMAIL = config.get("OUTREACH_FROM_EMAIL", "r-matsuno@terra-ltd.co.jp")
OUTREACH_MAIL_PASSWORD = config.get("OUTREACH_MAIL_PASSWORD", config.get("SESSALES_MAIL_PASSWORD", ""))
MATSUNO_EMAIL = "r-matsuno@terra-ltd.co.jp"
```

## 注意
- OUTREACH_FROM_EMAILとOUTREACH_MAIL_PASSWORDが.envに未設定の場合は
  松野アドレス（r-matsuno@terra-ltd.co.jp）とSESSALES_MAIL_PASSWORDでフォールバック
