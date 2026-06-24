import os

base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
ai_dir = os.path.join(base, "attachment_importer")

for root, dirs, files in os.walk(ai_dir):
    level = root.replace(ai_dir, "").count(os.sep)
    indent = "  " * level
    print(f"{indent}{os.path.basename(root)}/")
    for f in files:
        fpath = os.path.join(root, f)
        print(f"{indent}  {f}: {os.path.getsize(fpath)} bytes")
