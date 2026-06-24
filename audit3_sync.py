import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

print("=" * 70)
print("STEP-3: 2ファイルの完全同期チェック（line_webhook vs line_query）")
print("=" * 70)

p1 = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
p2 = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py"

with open(p1, "r", encoding="utf-8") as f:
    s1 = f.read()
with open(p2, "r", encoding="utf-8") as f:
    s2 = f.read()

if s1 == s2:
    print("✅ 2ファイル完全一致")
else:
    print("❌ 2ファイルに差異あり")
    # 差分を特定
    lines1 = s1.splitlines()
    lines2 = s2.splitlines()
    diffs = []
    for i, (l1, l2) in enumerate(zip(lines1, lines2), 1):
        if l1 != l2:
            diffs.append(f"  L{i}: \n    file1: {l1[:80]!r}\n    file2: {l2[:80]!r}")
    if len(lines1) != len(lines2):
        print(f"  行数: file1={len(lines1)}, file2={len(lines2)}")
    for d in diffs[:10]:
        print(d)
    if len(diffs) > 10:
        print(f"  ...他{len(diffs) - 10}箇所")

print()
print("=" * 70)
print("STEP-4: requirements.txt / 依存パッケージ確認")
print("=" * 70)

import os

req_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\requirements.txt"
if os.path.exists(req_path):
    with open(req_path, "r", encoding="utf-8") as f:
        reqs = f.read()
    print("requirements.txt:")
    for line in reqs.strip().splitlines():
        print(f"  {line}")

    for pkg in ["jpholiday", "python-dateutil", "requests", "flask", "python-dotenv"]:
        ok = any(pkg.lower() in line.lower() for line in reqs.splitlines())
        print(f"  {'✅' if ok else '❌'} {pkg}")
else:
    print("❌ requirements.txt が見つかりません")
