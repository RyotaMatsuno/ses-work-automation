# 実際のREVIEWケースで何が起きているか確認
# structured.jsonl から required_skills の中身と、missing の中身を照合

import json

structured_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\logs\structured.jsonl"
results_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\logs\phase0_results.jsonl"
aliases_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\skill_aliases.json"

# aliases 読み込み
with open(aliases_path, encoding="utf-8") as f:
    data = json.load(f)
hard = {k.lower(): v for k, v in data["aliases"].items()}


def normalize(skill):
    key = " ".join(skill.lower().strip().split())
    return hard.get(key, None)


# structured.jsonl から最初の5件のrequired_skillsを確認
print("=== structured.jsonl required_skills サンプル ===")
with open(structured_path, encoding="utf-8") as f:
    for i, line in enumerate(f):
        d = json.loads(line)
        req = d.get("required_skills", [])
        if req:
            print(f"case_id: {d.get('case_id', '?')[:8]}...")
            print(f"  required_skills: {req}")
            for s in req:
                n = normalize(s)
                print(f"    '{s}' -> normalize: {n}")
            print()
        if i >= 4:
            break
