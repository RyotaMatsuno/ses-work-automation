import sys

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from datetime import datetime

from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
headers = {
    "Authorization": f"Bearer {config['NOTION_API_KEY']}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

content = f"""{datetime.now().strftime("%Y-%m-%d")} matching_v2 精度改善 完了

■ 実装内容（Codexで自動実装済み）
  1. 単価フィルタ追加（evaluate_candidate）
     エンジニア単価 > 案件予算 + 5万円 の場合はスキル判定前にスキップ
     どちらかがNoneの場合はフィルタしない（情報不足案件は候補に残す）
  2. result.jsonにbudget（案件予算）追加（make_project_result）
  3. 尚可スキルあり件数の集計ログ追加（main末尾）
  4. notify_line.py: needs_check=Trueの候補者行に「⚠️要確認」追記済み（実装済みを確認）
  5. --sample で動作確認OK: returncode=0

■ 確認済み
  - py_compile matching_v2.py / notify_line.py → エラーなし
  - python matching_v2/matching_v2.py --sample → 正常終了
  - result.jsonにbudgetフィールド追加確認

■ 残タスク（このチャット範囲外）
  - アポ取りシステム本番送信（FP新営業アドレス・送信者名が決まったら即実行）
  - 岡本LINE Webhook疎通確認（岡本設定待ち）
"""

res = requests.patch(
    "https://api.notion.com/v1/blocks/353450ff-37c0-8145-9e3e-d80c8c8ed594/children",
    headers=headers,
    json={
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": content}}]},
            }
        ]
    },
)
print(f"Notion Wiki更新: {res.status_code}")
