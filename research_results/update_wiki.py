import sys, os, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests

api_key = os.environ.get("NOTION_API_KEY", "")
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

block_id = "353450ff-37c0-8145-9e3e-d80c8c8ed594"

entry = """## 2026-06-19 全システム包括調査＋バグ修正17件

### 発見・修正した問題
- BTM/NBW案件がengineer誤判定→skipされていた（正規表現1箇所修正）
- Notion API 400時に全エンジニアがマッチング対象になるバグ（RuntimeError送出に変更）
- Notion登録失敗でprocessed=1→案件永久欠損（成功時のみprocessed化に修正）
- pipelineがCostGuard v2未統合で暴走リスク（統合+fail-close化完了）
- 語彙外必須スキル31件がsilent pass→MATCH化（REVIEW化に修正）
- soft-skill all-pass未実装（config/soft_skills.json追加で対応）
- freee monthly承認ゲートなし並行稼働（即時退役）
- FT階段粗利75%/80%未実装（契約マスター連携で実装）
- 分類精度問題: 案件メール141件がother判定（Project優先判定ルール追加で修正中）

### 学んだこと
- gate_checkerのGPTが「Notion APIにもCostGuard必要」と繰り返し誤判定する→システムプロンプトに明示的除外が必要
- Gemini無料枠は枯渇する→第2レビュアーをClaude Sonnet APIに差替え
- PROCESS_LIMIT引き上げでバックログ消化すると分類精度の問題が表面化する
- fail-open（エラー時に制限なし）は暴走の根本原因。fail-close（エラー時に停止）が正しい
- GOオーバーライド: gate_checkerがNGでも的外れな指摘なら却下してGO判定にする運用

### コスト実績
- 6月累計: $0.55/$140（19日時点）
- 今日: $0.40/54コール（PROCESS_LIMIT=100）
- gate_checker Sonnet差替え後: +$1.44/月見込み"""

children = [
    {
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": entry[:2000]}}]
        }
    }
]

res = requests.patch(
    f"https://api.notion.com/v1/blocks/{block_id}/children",
    headers=headers,
    json={"children": children},
    timeout=30
)

if res.status_code == 200:
    print("SESナレッジWiki更新完了")
else:
    print(f"エラー: {res.status_code} {res.text[:200]}")
