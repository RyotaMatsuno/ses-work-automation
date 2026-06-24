import os

from dotenv import dotenv_values

env = dotenv_values("config/.env")

# Drive関連キーを確認
drive_keys = [
    k for k in env if "drive" in k.lower() or "google" in k.lower() or "oauth" in k.lower() or "service" in k.lower()
]
print("Drive/Google related keys:", drive_keys)

# token.jsonがあるか
for f in ["token.json", "credentials.json", "service_account.json"]:
    exists = os.path.exists(f)
    print(f"{f}: {'exists' if exists else 'NOT FOUND'}")

# config/以下も確認
for f in os.listdir("config"):
    print(f"config/{f}")
