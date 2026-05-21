import os

startup = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup")
vbs_path = os.path.join(startup, "skill_reader_api.vbs")

ses_work = os.path.expandvars(r"%USERPROFILE%\OneDrive\デスクトップ\ses_work")

vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "{ses_work}"
WshShell.Run "pythonw skill_reader\\skill_reader_api.py", 0, False
'''

with open(vbs_path, "w", encoding="utf-8") as f:
    f.write(vbs_content)

print(f"スタートアップ登録完了: {vbs_path}")
print("存在確認:", os.path.exists(vbs_path))
