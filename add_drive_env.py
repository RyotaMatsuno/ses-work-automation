# .envにDRIVE関連キーを追記
env_path = "config/.env"
with open(env_path, "r", encoding="utf-8") as f:
    content = f.read()

additions = []
if "DRIVE_FOLDER_ID" not in content:
    additions.append("DRIVE_FOLDER_ID=1zOO_kWSvf5AJgMckPIKKtNzbOUlB27jR")
if "GOOGLE_SA_FILE" not in content:
    additions.append("GOOGLE_SA_FILE=config/service_account.json")

if additions:
    with open(env_path, "a", encoding="utf-8") as f:
        f.write("\n# Google Drive attachment upload\n")
        for line in additions:
            f.write(line + "\n")
    print("Added to .env:", additions)
else:
    print("Already set.")
