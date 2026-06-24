import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\CLAUDE.md")
print(p.read_text(encoding="utf-8"))
