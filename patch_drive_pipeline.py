
path = "mail_pipeline/mail_pipeline.py"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

# === Patch 3: engineer処理ブロックにDriveアップロード追加 ===
# skill_result設定後、register_engineer呼び出しの前に挿入
old_eng = '''            # Notion登録
            ok, notion_id = register_engineer(info, subject, sender, input_source, affiliation)'''

new_eng = '''            # Drive添付アップロード
            drive_url = None
            if attachments:
                try:
                    from mail_pipeline.drive_uploader import upload_to_drive
                    att = attachments[0]
                    drive_url = upload_to_drive(att["filename"], att["data"], att["mime"])
                    if drive_url:
                        log(f"  [Drive] {drive_url}")
                except Exception as _de:
                    log(f"  [Drive] upload error: {_de}")

            # Notion登録
            ok, notion_id = register_engineer(info, subject, sender, input_source, affiliation, drive_url=drive_url)'''

src = src.replace(old_eng, new_eng)
print("Patch 3 (engineer Drive upload):", "OK" if "drive_uploader" in src else "FAILED")

# === Patch 4: project処理ブロックにDriveアップロード追加 ===
old_proj = '''            draft_path = save_draft(proj_name, reply_to, candidates,
                                    check_result, final_proposal, skill_result,
                                    from_account)'''

new_proj = '''            # Drive添付アップロード（案件メール添付）
            proj_drive_url = None
            if attachments:
                try:
                    from mail_pipeline.drive_uploader import upload_to_drive
                    att = attachments[0]
                    proj_drive_url = upload_to_drive(att["filename"], att["data"], att["mime"])
                    if proj_drive_url:
                        log(f"  [Drive] {proj_drive_url}")
                except Exception as _de:
                    log(f"  [Drive] upload error: {_de}")

            draft_path = save_draft(proj_name, reply_to, candidates,
                                    check_result, final_proposal, skill_result,
                                    from_account)'''

src = src.replace(old_proj, new_proj)
print("Patch 4 (project Drive upload):", "OK" if "proj_drive_url" in src else "FAILED")

with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("Saved.")
