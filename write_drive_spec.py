spec = """# SPEC.md - Drive Attachment Uploader

## Overview
When mail_pipeline.py processes emails with attachments (PDF/Excel/Word/image),
automatically upload the file to Google Drive and store the public link in Notion,
so that notify_line.py can include the Drive link in LINE messages.

## Target files
- ses_work/mail_pipeline/mail_pipeline.py  (add upload call)
- ses_work/matching_v2/notify_line.py      (add Drive link display in LINE message)

## New module to create
ses_work/mail_pipeline/drive_uploader.py

### drive_uploader.py - function: upload_to_drive(filename, data_bytes, mime_type) -> str | None
- Load credentials from config/service_account.json (path relative to ses_work/)
- Load DRIVE_FOLDER_ID from config/.env using dotenv_values
- Upload file to the folder
- Set permission: type=anyone, role=reader (public link)
- Return webViewLink (str) on success, None on any error
- On error: print error message, return None (never raise)
- Lazy import: import google libs inside function to avoid top-level import errors

### Dependencies (already installed, verify before use)
- google-auth
- google-api-python-client
- python-dotenv

## Changes to mail_pipeline/mail_pipeline.py

### Location 1: after process_skill_sheet() for engineer emails (~line 870-910)
After skill_result is set, if attachments exist:
```python
drive_url = None
if attachments:
    from mail_pipeline.drive_uploader import upload_to_drive
    att = attachments[0]
    drive_url = upload_to_drive(att["filename"], att["data"], att["mime"])
    if drive_url:
        log(f"  [Drive] uploaded: {drive_url}")
```
Then pass drive_url to register_engineer() as keyword arg drive_url=drive_url.

### Location 2: after process_skill_sheet() for project emails (~line 870)
Same pattern, pass drive_url to register_project() (or save in draft).

### Changes to register_engineer() and register_project()
Add optional parameter: drive_url: str = None
If drive_url is provided, write it to Notion property "Driveリンク" (rich_text field).
"Driveリンク" field already exists in the DB schema.

## Changes to matching_v2/notify_line.py

### In build_project_message() after raw_body section:
For each candidate, if engineer_info["drive_url"] is non-empty:
```
【添付ファイル】
{drive_url}
```

### In get_page_info() for engineers:
Already retrieves drive_url from Notion "Driveリンク" field (line 265 area).
Verify this is passed through to candidate_infos correctly.

## Acceptance criteria
1. Run python mail_pipeline/mail_pipeline.py with an email containing attachment
   -> Drive folder gets a new file
   -> Notion engineer page has "Driveリンク" filled
   -> result.json candidate has drive_url non-empty
2. Run python matching_v2/notify_line.py --dry-run
   -> LINE message text contains the Drive URL under "【添付ファイル】"
3. Emails without attachments: zero behavior change

## Error handling
- Drive upload failure: log warning, set drive_url=None, continue (do NOT abort pipeline)
- Missing service_account.json: log error, skip upload silently
"""

with open("mail_pipeline/SPEC_drive.md", "w", encoding="utf-8") as f:
    f.write(spec)
print("SPEC_drive.md written")
