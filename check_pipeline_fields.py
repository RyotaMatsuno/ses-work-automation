# mail_pipeline.pyで案件をどう登録しているか確認
path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline.py"
with open(path, encoding="utf-8") as f:
    lines = f.readlines()

# 案件登録部分（業務内容・案件詳細）を探す
for i, line in enumerate(lines):
    if any(k in line for k in ["案件詳細", "業務内容", "description", "content", "body", "本文", "メール本文"]):
        print(f"{i + 1}: {line}", end="")
