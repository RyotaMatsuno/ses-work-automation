# Codexログの末尾30行を確認
path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\codex_drive_fix.log"
with open(path, "r", encoding="utf-8", errors="replace") as f:
    lines = f.readlines()
print(f"Total lines: {len(lines)}")
for line in lines[-20:]:
    print(line.rstrip())
