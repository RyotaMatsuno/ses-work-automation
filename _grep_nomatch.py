import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# matching_v3 配下の全ファイルで「マッチ案件なし」を grep
result = subprocess.run(
    [
        "python",
        "-c",
        """
import os
for root, dirs, files in os.walk("matching_v3"):
    dirs[:] = [d for d in dirs if "__pycache__" not in d]
    for f in files:
        if not f.endswith(".py"):
            continue
        p = os.path.join(root, f)
        try:
            content = open(p, encoding="utf-8", errors="replace").read()
        except:
            continue
        if "マッチ案件なし" in content or "no_match_msg" in content.lower() or "match_result" in content.lower():
            print(f"FOUND: {p}")
            # 周辺を表示
            idx = content.find("マッチ案件なし")
            if idx != -1:
                print(content[max(0,idx-200):idx+400])
""",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
)
print(result.stdout or "(not found in matching_v3)")
print(result.stderr[:500] if result.stderr else "")

# line_webhookも確認
result2 = subprocess.run(
    [
        "python",
        "-c",
        """
import os
for root, dirs, files in os.walk("."):
    dirs[:] = [d for d in dirs if "__pycache__" not in d and ".git" not in d and "_archive" not in d]
    for f in files:
        if not (f.endswith(".py") or f.endswith(".md")):
            continue
        p = os.path.join(root, f)
        try:
            content = open(p, encoding="utf-8", errors="replace").read()
        except:
            continue
        if "マッチ案件なし" in content:
            print(f"FOUND: {p}")
""",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
)
print("\n=== 全体検索 ===")
print(result2.stdout or "(not found anywhere)")
