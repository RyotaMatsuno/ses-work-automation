import os

base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
path = os.path.join(base, "mail_pipeline", "mail_pipeline.py")
with open(path, encoding="utf-8") as f:
    lines = f.readlines()

# classify_email前後（411-430行）
print("=== classify_email ===")
for i in range(408, 432):
    print(f"{i + 1}: {lines[i]}", end="")

print("\n=== register_project（案件詳細） ===")
for i in range(520, 550):
    print(f"{i + 1}: {lines[i]}", end="")
