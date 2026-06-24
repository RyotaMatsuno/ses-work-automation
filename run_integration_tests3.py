import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"

# 8. line_query.pyのhandle_line_queryを実データでテスト（Notion接続）
print("=== TEST8: line_query classify_query ロジックテスト ===", flush=True)
sys.path.insert(0, os.path.join(BASE, "line_webhook"))

import re


def classify_query_test(text):
    stripped = text.strip()
    _m = re.match(r"^([A-Za-z.]{1,8})[\s\u3000/]+(.+)$", stripped)
    if _m:
        _raw = _m.group(1).strip(".")
        _sta = _m.group(2).strip()
        if re.match(r"^[A-Za-z.]+$", _raw) and len(_raw) >= 1:
            _ini = re.sub(r"[.]", "", _raw).upper()
            return ("engineer", {"initial": _ini, "station": _sta})
    return ("project", {"name": stripped})


cases = [
    "HS 北小金",
    "H.S 北小金",
    "TK 渋谷",
    "某金融系Java開発",
    "Oracle DBマイグレーション",
    "詳細 ①",
    "岡本の意向確認状況",
    "某案件 T.S 渋谷 催促",
]

for c in cases:
    qtype, params = classify_query_test(c)
    print(f'  "{c}" → {qtype}: {params}', flush=True)

# 9. mail_pipelineの送信ロジックFrom切り替えテスト
print("\n=== TEST9: send_counter.json From切り替えロジック ===", flush=True)
import json

counter_path = os.path.join(BASE, "config/send_counter.json")
with open(counter_path, encoding="utf-8") as f:
    counter = json.load(f)


def get_from_address_test(assignee, counter):
    """岡本2:松野1の交互割り振り"""
    if assignee == "松野":
        return "r-matsuno@terra-ltd.co.jp", "matsuno"
    elif assignee == "岡本":
        return "r-okamoto@terra-ltd.co.jp", "okamoto"
    else:
        # 交互: okamoto: 0,1 → matsuno: 2 → okamoto: 3,4 → matsuno: 5...
        total = counter.get("matsuno", 0) + counter.get("okamoto", 0)
        if total % 3 == 2:
            return "r-matsuno@terra-ltd.co.jp", "matsuno"
        else:
            return "r-okamoto@terra-ltd.co.jp", "okamoto"


for assignee in ["松野", "岡本", "", "共通"]:
    addr, who = get_from_address_test(assignee, counter)
    print(f'  担当者="{assignee}" → From: {addr}', flush=True)

# 交互テスト
print("  交互割り振りシミュレーション（6回）:", flush=True)
sim_counter = {"matsuno": 0, "okamoto": 0}
for i in range(6):
    addr, who = get_from_address_test("", sim_counter)
    sim_counter[who] += 1
    print(f"    {i + 1}回目: {who} ({addr})", flush=True)
