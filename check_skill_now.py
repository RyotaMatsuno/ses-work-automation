import os, glob

log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\logs\skill_autofill_codex.log"
size = os.path.getsize(log_path)
print(f"=== log ({size} bytes) ===")
if size > 0:
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        print(f.read()[-1500:])
else:
    print("(empty - Codex still running)")

print("\n=== pipeline_v1/ .py files ===")
for f in sorted(glob.glob(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pipeline_v1\*.py")):
    print(os.path.basename(f))
