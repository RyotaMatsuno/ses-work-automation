import json
from collections import Counter

path = r"matching_v3\logs\phase0_results.jsonl"
ambig_counter = Counter()

with open(path, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        for r in obj.get("results", []):
            if r.get("verdict") == "REVIEW":
                for reason in r.get("reasons", []):
                    if reason.startswith("曖昧スキルあり"):
                        # 曖昧スキルあり: ['xxx', 'yyy'] の形式
                        try:
                            skills_part = reason.split(":", 1)[1].strip()
                            skills = json.loads(skills_part.replace("'", '"'))
                            for s in skills:
                                ambig_counter[s] += 1
                        except:
                            ambig_counter[reason] += 1

lines = ["曖昧スキルのトップ30:"]
for skill, cnt in ambig_counter.most_common(30):
    lines.append(f"  {cnt:5d}  {skill}")

with open("diag_ambig.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("done")
