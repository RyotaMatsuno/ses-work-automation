import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES = os.getcwd()

# run_pipeline.bat の現状を再確認
bat_path = Path(SES) / "mail_pipeline" / "run_pipeline.bat"
print("■ run_pipeline.bat 現状")
with open(bat_path, encoding="cp932", errors="replace") as f:
    print(f.read())
