"""test_run.py - 完全版テスト（--mail出力まで確認）"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from skill_reader import run

# サンプルスキルシートをファイルに書いてテスト
SAMPLE = """
氏名: OA（33歳・女性）
最寄り駅: 東京メトロ 恵比寿駅
稼働: 即日
単価: 60万円

【スキル】
・Java（5年）: Spring Boot, Struts
・C#（2年）: .NET Framework
・React（1年）: フロントエンド実装

【経験工程】
基本設計、詳細設計、製造、テスト

【自己PR】
Javaメインで基本設計から製造まで一貫して対応可能。
C#・Reactの経験もあり幅広い案件に対応できます。
"""

# テキストファイルとして書き出してテスト
import tempfile

tmp = tempfile.mktemp(suffix=".txt")
with open(tmp, "w", encoding="utf-8") as f:
    f.write(SAMPLE)

print("=" * 60)
print("完全版テスト: OA（60万・Java/C#/React）")
print("  --mail オプションで意向確認文まで出力")
print("=" * 60 + "\n")

result = run(file_path=tmp, engineer_price=60, affiliation="アナリックス株式会社", output_mail=True)

print("\n--- 粗利ジャスト案件サマリー ---")
just = [r for r in result["match_results"] if r["proposable"] and r["gross"] and 5 <= r["gross"] <= 12]
for r in just:
    print(f"  {r['project_name']} | 粗利{r['gross']}万")
