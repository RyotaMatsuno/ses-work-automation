# SPEC.md - SES Pipeline 全機能統合

## SPEC-A: drive_uploader.py（新規作成）

### ファイルパス
ses_work/drive_uploader.py

### 機能
1. upload_to_drive(file_path: str) -> str
   - config/drive_token.json からOAuth認証情報を読み込み
   - token構造: {access_token, refresh_token, client_id, client_secret}
   - Credentials作成: google.oauth2.credentials.Credentials
   - token_uri: https://oauth2.googleapis.com/token
   - 期限切れ時は自動リフレッシュしてdrive_token.jsonに保存
   - Google Drive APIでファイルをアップロード
   - 共有設定: type=anyone, role=reader
   - webViewLink を返す

2. extract_spreadsheet_url(text: str) -> str | None
   - テキストから docs.google.com/spreadsheets のURLを正規表現で抽出
   - 見つかった場合はそのURLを返す（再アップ不要）
   - 見つからない場合は None を返す

### 依存ライブラリ（インストール済み確認済み）
- google-auth==2.53.0
- google-api-python-client==2.196.0

---

## SPEC-B: mail_pipeline/mail_pipeline.py 修正

### B-1: メール受信時の処理追加
既存の受信処理に以下を追加する:

1. Message-ID保存
   - 受信メールのMessage-IDヘッダーを取得
   - 案件DBの「元MessageID」フィールドに保存（案件として登録された場合）

2. 原文保存
   - メール本文全文を「案件情報原文」または「人員情報原文」フィールドに保存
   - 分類結果(project/engineer)によって保存先DBを切り替える

3. 添付ファイル処理
   - 添付ファイルあり → attachments/{notion_page_id}/ に保存
   - Excelファイル(.xlsx/.xls) → drive_uploader.upload_to_drive() でアップロード → DriveリンクURLをNotionに保存
   - Gmail/メール本文にdocs.google.com/spreadsheetsのURLあり → drive_uploader.extract_spreadsheet_url()で抽出 → DriveリンクURLに保存（再アップ不要）
   - エンジニアDBの場合: 「添付ファイルパス」「DriveリンクURL」フィールドに保存
   - 案件DBの場合: 「元MessageID」「案件情報原文」フィールドに保存

### B-2: メール送信時の処理修正
既存の提案メール送信処理を以下に変更する:

1. Fromアドレス切り替え
   - 案件DBの「担当者」フィールドを取得
   - 担当者=松野 → From: r-matsuno@terra-ltd.co.jp / OUTLOOK_EMAIL認証
   - 担当者=岡本 → From: r-okamoto@terra-ltd.co.jp / 岡本メール認証
   - 未設定/共通 → config/send_counter.jsonで交互管理（岡本2:松野1）
   - send_counter.json構造: {"matsuno": 0, "okamoto": 0}

2. 返信形式（In-Reply-To）
   - 案件DBの「元MessageID」が存在する場合:
     - MIMEMultipart作成後にヘッダー付与
     - msg['In-Reply-To'] = 元MessageID
     - msg['References'] = 元MessageID
   - 本文末尾に引用ブロック追加:
     ------ 元のメッセージ ------
     {案件情報原文}

3. 添付ファイル
   - エンジニアDBの「添付ファイルパス」を参照
   - MIMEBase でファイル添付
   - 添付なしの場合はそのまま送信（エラーにしない）
   - DRY_RUN=1 時は送信せずにログ出力のみ

---

## SPEC-C: matching_v2/notify_line.py 修正

### 既存の通知フォーマット変更

#### トリガー1: 提案可能通知（意向確認が返ってきた時）
送信先: 案件担当者のLINE user_id
フォーマット:
```
【提案可】
━━━━ 案件 ━━━━
{案件情報原文 全文}

━━━━ 候補 ━━━━
{人員情報原文 全文}

📎 スキルシート：{DriveリンクURL}
仕入：{単価（万円）}万
```
DriveリンクURLが空の場合は「📎 スキルシート：なし」と表示
仕入単価は案件DBの「仕入単価（万円）」フィールドから取得

---

## SPEC-D: line_webhook/webhook_server.py 修正

### 追加するコマンド処理

#### コマンド1: 催促コマンド
受信パターン: メッセージの末尾が「催促」で終わる
例: "某金融系Java開発 T.S 渋谷 催促"
パース方法: 末尾の「催促」を除いた部分をスペースで分割
  - 最後の要素 = 最寄り駅
  - 最後から2番目 = イニシャル
  - 残り = 案件名（スペース結合）

処理フロー:
1. 案件DBを案件名で検索 → 「案件情報原文」を取得
2. エンジニアDBをイニシャル（名前フィールドの部分一致）＋最寄り駅（備考フィールド等）で検索
   → 「人員情報原文」「DriveリンクURL」「所属メール」「所属担当者名」を取得
3. 所属メールに以下のメールを送信（SPEC-Bのから切り替えロジック適用）:

件名: 【ご意向確認のお願い】{案件名}
本文:
{案件情報原文 全文}
---
候補：{イニシャル}（{最寄り駅}）

{人員情報原文 全文}

📎 スキルシート：{DriveリンクURL}

→ ご意向をお聞かせください

4. 送信完了をLINE Reply APIで返信:
「{案件名} / {イニシャル}（{最寄り駅}）に催促メール送信しました」

#### コマンド2: 進捗確認コマンド
受信パターン: 「岡本の意向確認状況」または「松野の意向確認状況」

処理フロー:
1. 対象担当者の案件DBを取得
2. ステータスが「意向確認中」のレコードを抽出
3. 意向確認依頼日からの経過日数を計算
4. LINE Reply APIで返信:

【意向未返信】
・{案件名} / {イニシャル}（{最寄り駅}）- {経過日数}日
・{案件名} / {イニシャル}（{最寄り駅}）- {経過日数}日

---

## 動作確認ポイント
- DRY_RUN=1 で全機能をメール送信・Drive書き込みなしでテスト
- 添付ファイルのアップロードとURL取得
- In-Reply-Toヘッダーの付与確認
- 催促コマンドのパース確認
- 進捗確認コマンドの返答確認
