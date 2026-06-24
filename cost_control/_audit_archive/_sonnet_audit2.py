import glob
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
out = []


def w(*a):
    out.append(" ".join(str(x) for x in a))


# 1. find the module that defines extract_skills_from_image / extract_skills_from_text
w("=== def extract_skills_from_image / _text location & model ===")
for p in glob.glob(os.path.join(BASE, "**", "*.py"), recursive=True):
    if ".git" in p or "_archive" in p:
        continue
    try:
        t = open(p, encoding="utf-8", errors="replace").read()
    except:
        continue
    if "def extract_skills_from_image" in t or "def extract_skills_from_text" in t:
        rel = p.replace(BASE, "")
        w(f"\n--- {rel} ---")
        lines = t.splitlines()
        for i, l in enumerate(lines, 1):
            s = l.strip()
            if (
                "def extract_skills" in s
                or "model" in l.lower()
                or "sonnet" in l.lower()
                or "haiku" in l.lower()
                or "media_type" in l
                or "image" in s
                and "base64" in s
            ):
                if not s.startswith("#"):
                    w(f"  {i}: {s[:130]}")

# 2. skill_judge fallback detail (lines 95-200)
w("\n=== skill_judge.py fallback logic (95-200) ===")
p = os.path.join(BASE, "matching_v2", "skill_judge.py")
lines = open(p, encoding="utf-8", errors="replace").read().splitlines()
for i in range(94, 200):
    if i < len(lines):
        s = lines[i].rstrip()
        if s.strip():
            w(f"  {i + 1}: {s[:130]}")

# 3. outlook_to_notion model
w("\n=== outlook/outlook_to_notion.py model lines ===")
p = os.path.join(BASE, "outlook", "outlook_to_notion.py")
if os.path.exists(p):
    lines = open(p, encoding="utf-8", errors="replace").read().splitlines()
    for i, l in enumerate(lines, 1):
        s = l.strip()
        if (
            "model" in l.lower() or "sonnet" in l.lower() or "haiku" in l.lower() or "claude-" in l
        ) and not s.startswith("#"):
            w(f"  {i}: {s[:130]}")
else:
    w("  NOT FOUND at outlook/ ; searching...")
    for q in glob.glob(os.path.join(BASE, "**", "outlook_to_notion.py"), recursive=True):
        w("  found:", q.replace(BASE, ""))

# 4. cost_calculator / ledger model price table (to ground Sonnet vs Haiku price)
w("\n=== price table (cost_calculator.py / common/ledger.py) ===")
for rel in ["usage_tracker/cost_calculator.py", "common/ledger.py"]:
    p = os.path.join(BASE, rel)
    if not os.path.exists(p):
        continue
    w(f"--- {rel} ---")
    for i, l in enumerate(open(p, encoding="utf-8", errors="replace").read().splitlines(), 1):
        if (
            "sonnet" in l.lower()
            or "haiku" in l.lower()
            or "gpt" in l.lower()
            or "price" in l.lower()
            or "1_000_000" in l
            or "/ 1000" in l
            or "input" in l.lower()
            and "0." in l
        ):
            s = l.strip()
            if not s.startswith("#") and len(s) < 140:
                w(f"  {i}: {s}")

with open(os.path.join(BASE, "_sonnet_audit2.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(out))
print("DONE")
