import sys

import requests

sys.stdout.reconfigure(encoding="utf-8")
from dotenv import dotenv_values

config = dotenv_values("config/.env")

headers = {
    "Authorization": f"Bearer {config['NOTION_API_KEY']}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

PAGE_ID = "353450ff-37c0-8145-9e3e-d80c8c8ed594"


def p(text):
    return {"type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}}]}}


def b(text):
    return {
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def h2(text):
    return {"type": "heading_2", "heading_2": {"rich_text": [{"type": "text", "text": {"content": text}}]}}


children = [
    p("━" * 40),
    h2("【実装メモ】2026-06-02 パイプライン統合 + LINEクエリ拡張"),
    p("━" * 40),
    h2("■ 完了した実装"),
    b("Google Drive OAuth認証（config/drive_token.json）- OAuthクライアント: 74735301292-op9eiut55..."),
    b("drive_uploader.py 新規作成 - upload_to_drive() / extract_spreadsheet_url() 実装"),
    b(
        "Notionフィールド追加: エンジニアDB（添付ファイルパス/DriveリンクURL/人員情報原文/最寄り駅/イニシャル）案件DB（元MessageID/案件情報原文/仕入単価）"
    ),
    b("mail_pipeline.py 受信処理: 添付ファイル自動保存・Drive自動アップロード・原文保存・MessageID保存"),
    b(
        "mail_pipeline.py 送信処理: Fromアドレス切り替え（案件担当者判定）・In-Reply-Toヘッダー・引用ブロック・ファイル添付"
    ),
    b("notify_line.py 提案可通知: 案件全文＋人員全文＋DriveリンクURL＋仕入単価を全文表示"),
    b("webhook_server.py 催促コマンド: 「案件名 イニシャル 最寄り駅 催促」→ 所属に全文メール自動送信"),
    b("webhook_server.py 進捗確認コマンド: 「岡本/松野の意向確認状況」→ 未返信リスト返答"),
    b("line_query.py 案件側マッチング詳細照会: 「案件名」→ 人員一覧 → 「詳細①」→ 人員全文+DriveURL"),
    b(
        "line_query.py classify_queryバグ修正: Oracle等英語始まり案件名がengineer誤判定されていた問題を修正（4文字以内に厳密化）"
    ),
    h2("■ LINEコマンド仕様（最終確定）"),
    b("「HS 北小金」→ マッチング案件一覧（既存）"),
    b("「詳細 ①」→ 案件全文（人員クエリ後）または人員全文+DriveURL（案件クエリ後）"),
    b("「案件名」→ マッチング人員一覧（追加）"),
    b("「案件名 イニシャル 最寄り駅 催促」→ 所属に催促メール自動送信"),
    b("「岡本/松野の意向確認状況」→ 意向確認中の未返信リスト"),
    h2("■ テスト結果"),
    b("drive_uploader単体テスト: ✅ アップロード成功・URL取得確認"),
    b("全ファイル構文チェック: ✅ mail_pipeline / notify_line / webhook_server / line_query"),
    b("classify_query修正7ケース: ✅ PASS（Oracleバグ修正含む）"),
    b("催促コマンドパース4ケース: ✅ PASS"),
    b("送信カウンター交互割り振り: ✅ 岡本2:松野1 確認"),
    h2("■ Cloud Runデプロイ履歴"),
    b("rev.00058-qc5: パイプライン統合（mail_pipeline/notify_line/webhook_server/drive_uploader）"),
    b("rev.00059-844: line_query拡張（案件側詳細照会・classify_queryバグ修正）"),
    h2("■ 注意事項・既知の制限"),
    b("DriveリンクURL・人員情報原文はメール受信時に自動保存される（既存登録エンジニアは空のまま）"),
    b("「詳細①」のキャッシュはCloud Runインスタンスのメモリ上。再起動やインスタンス切り替えで消える（仕様）"),
    b(
        "案件側マッチングの粗利上限: 15万超はフィルタ除外（ハードコード）→ 変更する場合はproject_query内の if gross > 15 を修正"
    ),
    b(
        "config/drive_token.jsonはCloud Runにコピー済み（line_webhook/config/drive_token.json）。リフレッシュ時はCloud Runの方も更新が必要"
    ),
]

resp = requests.patch(
    f"https://api.notion.com/v1/blocks/{PAGE_ID}/children", headers=headers, json={"children": children}
)
print(f"Notion書き込み: {resp.status_code}", flush=True)
if resp.status_code != 200:
    print(resp.text[:300], flush=True)
else:
    print("SESナレッジWikiにメモを追記しました ✅", flush=True)
