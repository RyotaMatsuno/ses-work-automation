import os

base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"

# matching_v2.py の修正確認
m2 = os.path.join(base, "matching_v2", "matching_v2.py")
if os.path.exists(m2):
    with open(m2, encoding="utf-8") as f:
        content = f.read()
    print("=== matching_v2.py ===")
    print("build_skill_text_for_engineer:", "build_skill_text_for_engineer" in content)
    print("raw_text:", "raw_text" in content)
    print("drive_url:", "drive_url" in content)
    print("file_path (engineer):", '"file_path"' in content)
else:
    print("matching_v2.py NOT FOUND")

# attachment_importer ファイル確認
ai_dir = os.path.join(base, "attachment_importer")
print("\n=== attachment_importer/ ===")
if os.path.exists(ai_dir):
    for f in sorted(os.listdir(ai_dir)):
        fpath = os.path.join(ai_dir, f)
        size = os.path.getsize(fpath)
        print(f"  {f}: {size} bytes")
else:
    print("  directory NOT FOUND")
