# SPEC.md - Phase1 営業パイプライン

最終更新: 2026-05-25

---

## 概要

SES営業の「意向確認 → 返信解析 → 提案文生成」を自動化するCLIパイプライン。
既存のmatching_v2（マッチング結果=result.json）を受け取り、提案まで一気通貫で処理する。

---

## フロー

```
result.json（matching_v2の出力）
  ↓
[Step1] 意向確認メール生成
  - 案件情報 + 候補者情報から所属向け意向確認メールを生成
  - テンプレート: 提案テンプレート集v1のテンプレート1/2準拠
  - 出力: sales_pipeline/drafts/ikoukakunin_{案件ID}_{候補者ID}.txt

[Step2] 意向確認メール送信（ses-mail経由）
  - ses-mail MCPは使わず、ses_work/mail_mcp/mail_server.py のHTTPサーバーを叩く
  - エンドポイント: POST http://localhost:8766/send
  - 送信前に内容をstdoutに表示し、dry_run=Trueの場合は送信しない
  - 送信ログ: sales_pipeline/logs/send_log.json

[Step3] 返信パーサー（手動トリガー）
  - ses-mailから未読メールを取得し、意向確認への返信を解析
  - 解析内容:
    - 並行状況（面談調整中/面談予定/結果待ち）→ 並行スコア算出
    - 必須スキル○×
    - 尚可スキル○×
  - 出力: sales_pipeline/parsed_replies/{メールID}.json

[Step4] 提案可否判定
  - 判断マニュアルv3の判定ロジックを実装
  - 並行スコア合計5.0以上 → 提案NG
  - 必須スキルに× → 提案対象外
  - 粗利5万円未満 → 提案NG
  - 出力: 判定結果をparsed_replies/{メールID}.jsonに追記

[Step5] 提案文生成
  - 提案テンプレート集v1のテンプレート3/4準拠
  - 3名パッケージ（松竹梅）で生成
  - サマリーアピール文はテンプレート5のルールに従いClaude APIで生成
  - 出力: sales_pipeline/drafts/proposal_{案件ID}.txt

[Step6] 提案メール送信（送信前確認あり）
  - Step2と同じmail_server.pyのHTTPサーバーを叩く
  - dry_run=True時は送信しない（デフォルトTrue）
```

---

## ファイル構成

```
sales_pipeline/
├── CLAUDE.md
├── SPEC.md
├── TASKS.md
├── pipeline.py          # メインエントリーポイント（CLI）
├── step1_generate.py    # Step1: 意向確認メール生成
├── step2_send.py        # Step2: メール送信
├── step3_parse.py       # Step3: 返信パーサー
├── step4_judge.py       # Step4: 提案可否判定
├── step5_proposal.py    # Step5: 提案文生成
├── step6_send_proposal.py  # Step6: 提案メール送信
├── templates.py         # テンプレート定義
├── drafts/              # 生成メール一時保存
└── logs/                # 送受信ログ
```

---

## 設定値（config/.envから読む）

- `NOTION_API_KEY`: Notion APIキー
- `ANTHROPIC_API_KEY`: Claude APIキー（Step5のサマリー生成用）
- `SESMAIL_HOST`: ses-mailサーバーホスト（デフォルト: localhost）
- `SESMAIL_PORT`: ses-mailサーバーポート（デフォルト: 8766）

---

## テンプレート定義（templates.py）

### 意向確認メール（テンプレート1）
```
件名: ◯◯様 案件ご検討のお願い（{職種・エリア}）
{所属会社名} {担当者名}様

いつもお世話になっております。

人員のご紹介ありがとうございます。
下記案件いかがでしょうか。
ご検討いただけますと幸いです。

また、エントリーいただける場合下記2点ご教授いただけますと幸いです。
・並行状況
・必須、尚可の○×

━━━━━━━━━━━━━━━━━━
■ 案件概要
━━━━━━━━━━━━━━━━━━
案件名    : {案件名}
業務内容  : {業務内容}
必須スキル: {必須スキル}
尚可スキル: {尚可スキル}
単価      : {提案単価}万円
期間      : {期間}
勤務地    : {勤務地}（リモート可否: {リモート}）
面談      : {面談回数}回
外国籍    : {外国籍可否}

━━━━━━━━━━━━━━━━━━
■ ご記入フォーマット
━━━━━━━━━━━━━━━━━━
▼必須スキル（○/×）
{必須スキルフォーマット}
▼尚可スキル（○/×）
{尚可スキルフォーマット}

▼並行状況
 例）
  ・A社: 面談調整中
  ・B社: 面談予定 2/2（○月○日）
  ・C社: 結果待ち 2/2（面談実施日 ○月○日）

何卒よろしくお願いいたします。
```

---

## 並行スコア定義（step4_judge.pyに実装）

| ステータス | スコア |
|---|---|
| 面談調整中 | 1.5 |
| 面談予定 | 2.0 |
| 結果待ち（1〜2日） | 2.5 |
| 結果待ち（3〜7日） | 2.0 |
| 結果待ち（8〜14日） | 1.5 |
| 結果待ち（15日超） | 1.0 |
| オファー中 | 5.0 |
| 合計5.0以上 → 提案NG |

---

## 入力フォーマット（result.json）

```json
[
  {
    "project_id": "xxx",
    "project_name": "案件名",
    "required_skills": ["Python", "AWS"],
    "preferred_skills": ["Docker"],
    "budget": 70,
    "location": "東京都",
    "remote": "一部リモート可",
    "start_date": "2026-06-01",
    "interview_count": 1,
    "foreign_ok": false,
    "candidates": [
      {
        "engineer_id": "yyy",
        "name": "山田 太郎",
        "affiliation": "株式会社ABC",
        "contact_email": "yamada@abc.co.jp",
        "proposed_price": 65,
        "required_match": {"Python": true, "AWS": true},
        "preferred_match": {"Docker": false},
        "parallel_status": [],
        "score": 0.85
      }
    ]
  }
]
```

---

## smoke test手順

```bash
cd C:\Users\ma_py\OneDrive\デスクトップ\ses_work
python sales_pipeline/pipeline.py --dry-run
```

期待する出力:
- `[Step1] 意向確認メール生成: N件`
- `[Step2] dry-run: メール送信スキップ`
- `[Step3] 未読メール確認: N件`
- `[Step4] 提案可否判定: N件OK / M件NG`
- `[Step5] 提案文生成: N件`
- `[Step6] dry-run: 提案メール送信スキップ`
```
