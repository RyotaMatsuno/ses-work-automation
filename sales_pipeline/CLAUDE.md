# CLAUDE.md - sales_pipeline Codex作業ルール
最終更新: 2026-05-25

## 役割
あなたはJobz（Claude Desktop）から指示を受けたコード実装専任エージェントです。
SPEC.mdを読み、TASKS.mdのチェックリスト順に実装してください。

## 作業ディレクトリ
`C:\Users\ma_py\OneDrive\デスクトップ\ses_work\sales_pipeline\`

## 禁止事項
- TASKS.mdの順番を変えること
- 実装済みタスクを再実装すること
- Notion APIをMCP経由で呼ぶこと（jobz-command経由でPython REST APIを直接叩くこと）
- 既存ファイル（matching_v2/, config/.env等）を書き換えること
- テストなしで「完了」にすること

## 必須ルール
- credentialは `config/.env` から `dotenv_values` で読み込む（パス: `C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env`）
- 文字コード: すべてのファイルはUTF-8で保存
- print出力: `print(..., flush=True)` を使う（バックグラウンド実行対応）
- Notion REST API: `https://api.notion.com/v1/`、ヘッダーにAPIキーとNotionバージョン必須
- エラー時は詳細なエラーメッセージをログに出力して処理を続ける（クラッシュしない）
- TASKS.mdの各タスク完了後にチェックを入れること（`- [ ]` → `- [x]`）
- 各モジュールは200行以内を目安にする

## 既存インフラ（使ってよいもの）
- matching_v2/result.json: マッチング結果（案件×候補者）
- matching_v2/matching_v2.py: マッチングエンジン
- matching_v2/notify_line.py: LINE通知
- run_matching_and_notify.bat: バッチ実行スクリプト
- config/.env: 全APIキー格納

## エンコーディング注意
- Windows環境（cp932）のため、ログファイルはUTF-8で書き込む
- subprocess呼び出しでは `encoding='utf-8'` または `encoding='cp932'` を明示する
