import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# line_bridge の中で「マッチ案件なし」を生成している箇所を探す
result = subprocess.run(
    [
        "python",
        "-c",
        """
import os
for root, dirs, files in os.walk("line_webhook"):
    dirs[:] = [d for d in dirs if "__pycache__" not in d]
    for f in files:
        if not f.endswith(".py"):
            continue
        p = os.path.join(root, f)
        try:
            c = open(p, encoding="utf-8", errors="replace").read()
        except:
            continue
        if "マッチ案件なし" in c or "案件なし" in c or "PH" in c:
            print(f"\\n=== {p} ===")
            for kw in ["マッチ案件なし", "案件なし", "PH????", "no_match", "マッチなし"]:
                idx = c.find(kw)
                if idx != -1:
                    print(f"  [{kw}] at {idx}:")
                    print(c[max(0,idx-200):idx+400])
""",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
)
print(result.stdout or "(not found in line_webhook)")
