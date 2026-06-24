import sys

sys.stdout.reconfigure(encoding="utf-8")

env_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env"
with open(env_path, encoding="utf-8") as f:
    content = f.read()

# OKAMOTO系のキーが既にあるか確認
keys_to_check = ["OKAMOTO_EMAIL", "OKAMOTO_PASSWORD", "OKAMOTO_MAIL_PASSWORD"]
for k in keys_to_check:
    exists = k in content
    val = ""
    if exists:
        for line in content.split("\n"):
            if line.startswith(k + "="):
                val = line.split("=", 1)[1].strip()
    print(f"{k}: {'設定済み=' + val[:4] + '...' if exists and val else '未設定' if not exists else '空'}")
