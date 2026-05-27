import json, sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pipeline_v1\result_pipeline.json", encoding="utf-8") as f:
    d = json.load(f)

print(f"案件総数: {d['total_projects']}, マッチ: {d['matched_projects']}")
for item in d["items"]:
    p = item["project"]
    print(f"\n■ {p['name']}")
    print(f"  必須スキル: {p['required_skills']}")
    print(f"  尚可スキル: {p['optional_skills']}")
    for c in item["candidates"]:
        print(f"  候補: {c['name']} / {c['price']}万 / 粗利{c['gross_profit']}万")
        print(f"  メール:\n{c['draft_mail'][:300]}")
