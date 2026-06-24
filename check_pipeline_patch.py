import sys

sys.stdout.reconfigure(encoding="utf-8")

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\mail_pipeline.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

lines = content.split("\n")
print(f"Total lines: {len(lines)}")

# _derive_initial 検索
found_derive = False
found_extract = False
for i, line in enumerate(lines, 1):
    if "_derive_initial" in line:
        found_derive = True
        print(f"  [derive_initial] L{i}: {line.strip()}")
    if "_extract_affil" in line:
        found_extract = True
        print(f"  [extract_affil] L{i}: {line.strip()}")

if not found_derive:
    print("_derive_initial: NOT FOUND")
if not found_extract:
    print("_extract_affil: NOT FOUND")

# biko field references
print("\n=== biko / 備考 references ===")
for i, line in enumerate(lines, 1):
    raw = line
    # 備考をユニコードで検索
    if "\u5099\u8003" in raw or "biko" in raw.lower():
        print(f"  L{i}: {raw.strip()[:120]}")

# register_engineer 関数の範囲を確認
print("\n=== register_engineer function ===")
in_func = False
for i, line in enumerate(lines, 1):
    if "def register_engineer" in line:
        in_func = True
        print(f"  L{i}: {line.strip()}")
    elif in_func:
        if line.startswith("def ") and "register_engineer" not in line:
            print(f"  L{i}: [END - next def]")
            break
        if (
            "\u30a4\u30cb\u30b7\u30e3\u30eb" in line
            or "\u6240\u5c5e\u30e1\u30fc\u30eb" in line
            or "initial" in line.lower()
            or "affil" in line.lower()
        ):
            print(f"  L{i}: {line.strip()[:120]}")
