import sys

sys.stdout.reconfigure(encoding="utf-8")

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\mail_pipeline.py"
with open(path, encoding="utf-8") as f:
    lines = f.readlines()

# _derive_initial (L787) と _extract_affil_from_sender (L820) の実装を表示
print("=== _derive_initial (L787) ===")
for i in range(786, 820):
    print(f"L{i + 1}: {lines[i]}", end="")

print("\n=== _extract_affil_from_sender (L820) ===")
for i in range(819, 870):
    if i < len(lines):
        print(f"L{i + 1}: {lines[i]}", end="")

print("\n=== register_engineer L882-L930 ===")
for i in range(881, 930):
    if i < len(lines):
        print(f"L{i + 1}: {lines[i]}", end="")
