import sys

sys.stdout.reconfigure(encoding="utf-8")
import os

ses = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"

# matching_v2.py の粗利計算・マッチングロジック全体を確認
mv2_path = os.path.join(ses, "matching_v2", "matching_v2.py")
with open(mv2_path, encoding="utf-8") as f:
    lines = f.readlines()

# get_min_gross L225付近
print("=== matching_v2.py: get_min_gross & 閾値チェック L220-L270 ===")
for i in range(219, 270):
    if i < len(lines):
        print(f"L{i + 1}: {lines[i]}", end="")

# 粗利計算・除外ロジック L430-L480
print("\n=== L420-L480: 粗利計算・除外ロジック ===")
for i in range(419, 480):
    if i < len(lines):
        print(f"L{i + 1}: {lines[i]}", end="")

# result.jsonのH.S関連データを確認
import json

result_path = os.path.join(ses, "matching_v2", "result.json")
with open(result_path, encoding="utf-8") as f:
    data = json.load(f)

# H.SのエンジニアIDで絞り込み
hs_id = "36c450ff-37c0-813b-8f31-d38228e3cf2e"
hs_matches = []
for item in data:
    for c in item.get("candidates", []):
        eng = c.get("engineer") or {}
        if hs_id in (eng.get("id", ""), c.get("engineer_id", "")):
            hs_matches.append(item)
            break

print(f"\n\n=== H.S マッチング件数: {len(hs_matches)} ===")
for item in hs_matches[:5]:
    p = item.get("project") or {}
    pname = p.get("name") or item.get("project_name", "")
    pprice = p.get("price") or item.get("price")
    for c in item.get("candidates", []):
        eng = c.get("engineer") or {}
        if hs_id in (eng.get("id", ""), c.get("engineer_id", "")):
            eprice = eng.get("price") or c.get("price")
            gross = (pprice - eprice) if pprice and eprice else None
            print(f"  案件:{pname[:30]} 案件単価:{pprice} エンジニア単価:{eprice} 粗利:{gross} スコア:{c.get('score')}")
