
# run_collect.bat を作成（Windowsターミナル直接実行用）
bat_content = r"""@echo off
cd /d C:\Users\ma_py\OneDrive\デスクトップ\ses_work
python outreach_system\collect_targets.py --run
pause
"""

with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\run_collect.bat", "w", encoding="cp932") as f:
    f.write(bat_content)
print("Created: run_collect.bat")
