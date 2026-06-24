path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\matching_v2.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

print("build_skill_text_for_engineer:", "build_skill_text_for_engineer" in content)
print("raw_text:", '"raw_text"' in content)
print("drive_url:", '"drive_url"' in content)
print("skill_text:", '"skill_text"' in content)
