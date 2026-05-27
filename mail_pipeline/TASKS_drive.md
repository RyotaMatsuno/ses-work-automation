# TASKS.md - Drive Attachment Uploader

## Task 1: Create drive_uploader.py
- [ ] Create ses_work/mail_pipeline/drive_uploader.py
- [ ] Implement upload_to_drive(filename, data_bytes, mime_type) -> str | None
- [ ] Lazy import google libs inside function
- [ ] Load SA path from config/service_account.json (relative to ses_work root)
- [ ] Load DRIVE_FOLDER_ID from config/.env
- [ ] Set anyone/reader permission after upload
- [ ] Return webViewLink on success, None on exception

## Task 2: Patch mail_pipeline.py - engineer branch
- [ ] After existing skill_result block for engineer emails, add Drive upload call
- [ ] Import upload_to_drive lazily inside the if block
- [ ] Pass drive_url to register_engineer()

## Task 3: Patch mail_pipeline.py - project branch
- [ ] After existing skill_result block for project emails, add Drive upload call
- [ ] Pass drive_url to register_project() or save_draft()

## Task 4: Patch register_engineer() and register_project()
- [ ] Add drive_url: str = None parameter
- [ ] If drive_url: write to Notion "Driveリンク" property using split_rich_text()

## Task 5: Patch notify_line.py
- [ ] In build_project_message(), after raw_body section for each candidate:
      check eng_info.get("drive_url") and append "【添付ファイル】\n{url}" to lines
- [ ] Verify get_page_info() for engineers already reads "Driveリンク" field

## Task 6: Smoke test
- [ ] python mail_pipeline/drive_uploader.py  (unit test: upload test.txt to Drive)
- [ ] Verify file appears in Drive folder
- [ ] python matching_v2/notify_line.py --dry-run and check output contains Drive URL
