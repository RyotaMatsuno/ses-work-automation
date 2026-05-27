import sys
sys.stdout.reconfigure(encoding='utf-8')

matcher_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pipeline_v1\matcher.py"
with open(matcher_path, encoding="utf-8") as f:
    content = f.read()

# candidateオブジェクトにengineerが含まれているか確認
print("'engineer' in matcher.py:", "engineer" in content)
print("'affiliation' in matcher.py:", "affiliation" in content)

# candidateを組み立てている箇所を探す
idx = content.find("candidate")
print("\ncandidate構築部分:")
print(content[idx:idx+500] if idx >= 0 else "not found")
