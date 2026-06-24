import sys

sys.stdout.reconfigure(encoding="utf-8")

env_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env"
with open(env_path, encoding="utf-8") as f:
    content = f.read()

# 末尾に追記（改行確認してから）
add = "\n# 岡本アカウント（2026-05-29追加）\nOKAMOTO_EMAIL=r-okamoto@terra-ltd.co.jp\nOKAMOTO_PASSWORD=Egk:8gB3dr\n"

if "OKAMOTO_EMAIL" not in content:
    if not content.endswith("\n"):
        content += "\n"
    content += add
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("追記OK")
else:
    print("既に存在")
