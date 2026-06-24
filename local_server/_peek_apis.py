import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
for f in ["wall_hitting.py", "gpt_consult.py", "gemini_review.py", "run_codex_bg.py", "consult_arch.py"]:
    print("==== %s (%s) ====" % (f, "exists" if os.path.exists(f) else "MISSING"))
    if os.path.exists(f):
        print(open(f, encoding="utf-8", errors="replace").read()[:1200])
    print()
