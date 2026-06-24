import os

base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
path = os.path.join(base, "mail_pipeline", "mail_pipeline.py")
with open(path, encoding="utf-8") as f:
    lines = f.readlines()

# register_project呼び出し箇所を探す
for i, line in enumerate(lines):
    if "register_project(" in line:
        print(f"{i + 1}: {line}", end="")
        # 前後数行も表示
        for j in range(max(0, i - 3), min(len(lines), i + 4)):
            print(f"  {j + 1}: {repr(lines[j])}", end="")
        print()
