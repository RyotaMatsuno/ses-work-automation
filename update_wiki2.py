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
        "paragraph": {"rich_text": [t("[2026-06-03] matching_v3設計確定（GPT/Gemini壁打ち3回完了）")]},
        "type": "paragraph",
    },
    {
        "bulleted_list_item": {
            "rich_text": [
                t(
                    "設計: LLMは案件メールのJSON構造化のみ。マッチングはPythonのif文。モデルはHaikuで開発→精度確認後にGemini Flash-Lite差替え。"
                )
            ]
        },
        "type": "bulleted_list_item",
    },
    {
        "bulleted_list_item": {
            "rich_text": [t("コスト: 月$107（20営業日）。1日$6上限/月$140上限/Anthropic側$140のSpend Limit設定必須。")]
        },
        "type": "bulleted_list_item",
    },
    {
        "bulleted_list_item": {
            "rich_text": [t("精度: NG/REVIEW/MATCHの3段階判定。NGは自動除外（通知なし）、REVIEW/MATCHのみLINE通知。")]
        },
        "type": "bulleted_list_item",
    },
    {
        "bulleted_list_item": {
            "rich_text": [
                t(
                    "暴走防止: 5重+3防御壁（processed_id/回数上限/日次コスト/月次コスト/本文長制限/二重起動ロック/推定コスト予約/Anthropic Spend Limit）"
                )
            ]
        },
        "type": "bulleted_list_item",
    },
    {
        "bulleted_list_item": {
            "rich_text": [
                t(
                    "GPT/Gemini共通指摘: processed_idをステータスDB化、LLM構造化とNotion書き込み分離、曖昧スキルはoptionalに、Few-Shot5例、48時間取得方式。"
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
