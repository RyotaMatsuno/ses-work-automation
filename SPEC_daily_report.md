# SPEC_daily_report.md

## 目的
1. daily_report.py: 毎朝8時に案件進捗サマリーをLINEに送信（Push API 1通/日）
2. webhook_server.pyに「進捗」コマンド追加: LINEから「進捗」と送るとReply APIで返答

## ファイル
- 新規作成: ses_work/daily_report.py
- 修正: ses_work/line_webhook/webhook_server.py（「進捗」コマンド追加）

## Notion案件DBのフィールド（追加済み）
- 案件名: title
- ステータス: select（募集中/選考中/成約/終了/稼働中）
- 単価（万円）: number
- 担当者: select（松野/岡本/共通）
- 提案中: number
- 面談希望: number
- NG: number
- 合格: number
- 成約: number
- 営業終了: number

## daily_report.pyの仕様

### 取得対象
- ステータスが「募集中」「選考中」の案件のみ

### 送信先
- 担当者=松野 → 松野のLINEに送信
- 担当者=岡本 → 岡本のLINEに送信
- 担当者=共通 → 松野・岡本両方に送信
- 送信はPush API（LINE_CHANNEL_ACCESS_TOKEN / LINE_OKAMOTO_CHANNEL_ACCESS_TOKEN）

### メッセージフォーマット
```
【案件進捗】MM/DD（曜日）

■ {案件名}（{単価}万）
  提案中:{n} / 面談希望:{n} / NG:{n} / 合格:{n}

■ {案件名}（{単価}万）
  提案中:{n} / 面談希望:{n} / NG:{n} / 合格:{n}

⚡ 要アクション
  面談希望が1件以上ある案件を列挙
  （例）Java開発 → 面談希望2件
```

- 案件数が0件なら「本日募集中案件なし」を送信
- 成約・営業終了は件数が0以外なら表示、0なら省略
- 1通に収まらない場合（5000文字超）は分割してpush

### credentials
ENV_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env"
from dotenv import dotenv_values
config = dotenv_values(ENV_PATH)
NOTION_API_KEY = config["NOTION_API_KEY"]
MATSUNO_TOKEN = config["LINE_CHANNEL_ACCESS_TOKEN"]
MATSUNO_USER_ID = config["MATSUNO_LINE_USER_ID"]
OKAMOTO_TOKEN = config.get("LINE_OKAMOTO_CHANNEL_ACCESS_TOKEN") or config.get("OKAMOTO_LINE_CHANNEL_ACCESS_TOKEN","")
OKAMOTO_USER_ID = config.get("OKAMOTO_LINE_USER_ID","")

### 実行方法
python daily_report.py           # 本番送信
python daily_report.py --dry-run # 出力のみ（送信なし）

---

## webhook_server.pyへの「進捗」コマンド追加

### 追加箇所
process_message()内の「マッチング」コマンド分岐の直後に追加

### 条件
text_strippedが「進捗」を含み10文字以下

### 処理
1. Notion案件DBから募集中・選考中案件を全件取得
2. daily_report.pyと同じフォーマットで文字列を組み立て
3. Reply APIで返信（split_line_message()で分割）

### 注意
- Notion APIコールはrequestsで直接叩く（既存のnotion_query()を使う）
- 他の既存機能は変更しない
- credentials読み込みはファイル先頭の既存パターンをそのまま使う
