import sys, os, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests
from dotenv import dotenv_values

env_path = os.path.join(os.environ["USERPROFILE"], "OneDrive", "\u30c7\u30b9\u30af\u30c8\u30c3\u30d7", "ses_work", "config", ".env")
env = dotenv_values(env_path)
api_key = env.get("NOTION_API_KEY", "")

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

block_id = "353450ff-37c0-8145-9e3e-d80c8c8ed594"

entry = "## 2026-06-19 全システム包括調査+バグ修正17件\n\n### 発見・修正した問題\n- BTM/NBW案件がengineer誤判定でskip（正規表現修正）\n- Notion 400時に全員マッチング対象（RuntimeError送出に変更）\n- Notion登録失敗で案件永久欠損（成功時のみprocessed化）\n- pipelineがCostGuard v2未統合（統合+fail-close化完了）\n- 語彙外スキル31件がsilent pass（REVIEW化）\n- soft-skill all-pass未実装（config追加で対応）\n- freee monthly承認ゲートなし（即時退役）\n- FT階段粗利未実装（契約マスター連携で実装）\n- 分類精度: 案件141件がother判定（修正中）\n\n### 学んだこと\n- gate_checkerのGPTがNotion APIにCostGuard誤要求→プロンプト除外必要\n- Gemini無料枠は枯渇する→Claude Sonnet APIに差替え\n- fail-openは暴走の根本原因。fail-closeが正しい\n- PROCESS_LIMIT引上げで分類精度問題が表面化する\n\n### コスト実績\n- 6月累計: $0.55/$140（19日時点）\n- gate_checker Sonnet差替後: +$1.44/月見込み"

children = [{"type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": entry}}]}}]

res = requests.patch(
    f"https://api.notion.com/v1/blocks/{block_id}/children",
    headers=headers,
    json={"children": children},
    timeout=30
)
print(f"Status: {res.status_code}")
if res.status_code == 200:
    print("SES Wiki更新完了")
else:
    print(f"Error: {res.text[:200]}")
