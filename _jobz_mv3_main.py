import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES = os.getcwd()
mv3 = os.path.join(SES, "matching_v3", "matching_v3.py")

with open(mv3, encoding="utf-8") as f:
    lines = f.readlines()

# L60-L80 (main付近) と L295-L310 (2回目の_setup_logging付近) を確認
print("■ L60-L80 (main/_setup_logging呼び出し付近)")
for i, line in enumerate(lines[59:79], 60):
    print(f"  L{i}: {line.rstrip()}")

print("\n■ L295-L315 (2回目の_setup_logging付近)")
for i, line in enumerate(lines[294:315], 295):
    print(f"  L{i}: {line.rstrip()}")
