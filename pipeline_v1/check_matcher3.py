import sys

sys.stdout.reconfigure(encoding="utf-8")

matcher_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pipeline_v1\matcher.py"
with open(matcher_path, encoding="utf-8") as f:
    content = f.read()

idx = content.find("def calculate_match")
print(content[idx : idx + 1500])
