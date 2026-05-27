
import requests
from dotenv import dotenv_values
from datetime import datetime

cfg = dotenv_values("config/.env")
NOTION_TOKEN = cfg["NOTION_API_KEY"]
WIKI_PAGE_ID = "353450ff-37c0-8145-9e3e-d80c8c8ed594"

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

today = datetime.now().strftime("%Y-%m-%d %H:%M")

def t(content, bold=False):
    return {"type": "text", "text": {"content": content}, "annotations": {"bold": bold}}

def para(content, bold=False):
    return {"type": "paragraph", "paragraph": {"rich_text": [t(content, bold)]}}

def bullet(content):
    return {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [t(content)]}}

def num(content):
    return {"type": "numbered_list_item", "numbered_list_item": {"rich_text": [t(content)]}}

blocks = [
    {"type": "divider", "divider": {}},
    para(f"■ {today} 進捗メモ（Jobz自動記録）", bold=True),
    para("【完了確認済みシステム一覧】", bold=True),
    bullet("webhook_server.py v13: マッチング/進捗照会のReply API対応済み（Push API不使用・月制限なし）"),
    bullet("pipeline_v1/pipeline.py: dry-run完走。total_projects:4 matched:1 result_pipeline.json出力OK"),
    bullet("outreach_system/outreach.py: 全14タスク完了済み。dry-run動作確認OK"),
    bullet("local_server/watchdog.py: 正常稼働中（jobz-watchdog/JobzWatchdogタスクスケジューラ登録済み）"),
    bullet("jobz_matching_daily: 毎日08:00 タスクスケジューラ登録済み"),
    bullet("LINE user_id確認: 松野=Ue3508b4... / 岡本=Uac1d234...（別々の値で正常）"),
    para("【未完了・対応待ち】", bold=True),
    bullet("LINE月200通上限: 6/1リセット待ち。notify_line.py本番送信テストは6/1以降"),
    bullet("岡本LINE Webhook: save_session.py実行待ち（岡本側の作業）"),
    bullet(".envにOKAMOTO_LINE_CHANNEL_ACCESS_TOKEN追加: 松野が1行追加するだけ"),
    bullet("アポ取りシステム本番送信: 送信者名・FP新営業メールアドレス未確定"),
    bullet("Cloud Run再デプロイ: gcloud run deploy で line-webhook を更新する必要あり"),
    para("【次のアクション（優先順）】", bold=True),
    num("gcloud run deploy で line-webhook を再デプロイ（手動1回）"),
    num("6/1以降: notify_line.py本番送信テスト実行"),
    num("岡本に save_session.py 実行を依頼 → Webhook疎通確認"),
    num("FP新営業メールアドレスが決まり次第 .env に追加 → outreach_system 本番送信"),
]

resp = requests.patch(
    f"https://api.notion.com/v1/blocks/{WIKI_PAGE_ID}/children",
    headers=headers,
    json={"children": blocks}
)

if resp.status_code == 200:
    print(f"OK: Notion更新完了 ({today})")
else:
    print(f"NG: {resp.status_code} {resp.text[:200]}")
