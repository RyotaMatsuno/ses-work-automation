env_path = "config/.env"
with open(env_path, "r", encoding="utf-8") as f:
    content = f.read()

new_id = "1mROBOtu0xL0NuTTKd1NJdj0y-p6Rv1N4"
if "DRIVE_FOLDER_ID=1zOO_kWSvf5AJgMckPIKKtNzbOUlB27jR" in content:
    content = content.replace("DRIVE_FOLDER_ID=1zOO_kWSvf5AJgMckPIKKtNzbOUlB27jR", f"DRIVE_FOLDER_ID={new_id}")
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Updated DRIVE_FOLDER_ID -> {new_id}")
else:
    print("Old ID not found, current content:")
    print(content[-300:])
