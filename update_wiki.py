import json
import urllib.request

from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = config.get("NOTION_API_KEY")
block_id = "353450ff-37c0-8145-9e3e-d80c8c8ed594"


def t(text):
    return {"text": {"content": text}, "type": "text"}


children = [
    {
        "paragraph": {"rich_text": [t("[2026-06-03] APIコスト急増 → Auto-recharge2回発火 → 再発防止対策完了")]},
        "type": "paragraph",
    },
    {
        "bulleted_list_item": {
            "rich_text": [
                t(
                    "原因: mail_pipelineのDriveリンクURLフィールドをrich_text型で書いていたがNotionはurl型を要求 → 400エラーが毎回発生。1日17,621件のAPI呼び出しで$50.88消費。"
                )
            ]
        },
        "type": "bulleted_list_item",
    },
    {
        "bulleted_list_item": {
            "rich_text": [
                t("修正①: Codexでmail_pipeline.pyのDriveリンクURL書き込みをurl型に修正（add_url_if_exists経由）")
            ]
        },
        "type": "bulleted_list_item",
    },
    {
        "bulleted_list_item": {
            "rich_text": [
                t(
                    "修正②: cost_guard.py新設。1時間$3超でLINE警告、1日$15超でSES_MailPipeline/SES_MatchingAndNotifyを自動停止。SES_CostGuardタスクとして30分おきに実行。"
                )
            ]
        },
        "type": "bulleted_list_item",
    },
    {
        "bulleted_list_item": {
            "rich_text": [
                t(
                    "教訓: Notionフィールド型の確認は実装前に必須。url型フィールドにrich_textで書くと毎回400エラー。新フィールド追加時はCodexのSPECにNotion API仕様を明記すること。"
                )
            ]
        },
        "type": "bulleted_list_item",
    },
]

payload = json.dumps({"children": children}).encode("utf-8")
req = urllib.request.Request(
    f"https://api.notion.com/v1/blocks/{block_id}/children",
    data=payload,
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"},
    method="PATCH",
)
with urllib.request.urlopen(req, timeout=15) as r:
    res = json.loads(r.read())
    print(f"OK: {len(res.get('results', []))} blocks appended")
