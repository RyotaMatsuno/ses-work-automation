spec = """# SPEC_drive_patch.md - mail_pipeline & notify_line Drive integration patch

## What's done
- ses_work/mail_pipeline/drive_uploader.py: COMPLETE. upload_to_drive(filename, data_bytes, mime_type) -> str|None

## What to implement now

### 1. Patch mail_pipeline/mail_pipeline.py

#### Target: engineer email branch (~line 875-920)
Find the block that handles attachments for engineers:
```python
if attachments:
    log(f"  添付スキルシートを処理: {attachments[0]['filename']}")
    skill_result = process_skill_sheet(
        attachments[0], ...
    )
```
After skill_result is set (after the if attachments block), add:
```python
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
```

Then find register_engineer() call and add drive_url=drive_url parameter.

#### Target: project email branch (~line 855-875)
Same pattern - after skill_result block, add Drive upload, pass to register_project().

### 2. Patch register_engineer() function
Add parameter: drive_url: str = None
If drive_url: write to Notion property "Driveリンク" using split_rich_text() or direct rich_text list.
"Driveリンク" is already a rich_text field in Notion schema.

### 3. Patch register_project() function
Same as register_engineer() - add drive_url param, write to "Driveリンク" if set.

### 4. Patch matching_v2/notify_line.py

#### In build_project_message():
After the engineer raw_body section for each candidate, add:
```python
drive_url = eng_info.get("drive_url", "").strip()
if drive_url:
    lines.append("")
    lines.append(f"【添付ファイル】")
    lines.append(drive_url)
```

#### Verify get_page_info() for engineers already reads "Driveリンク":
Line ~265 area already has: "drive_url": get_text_property(props, "Driveリンク")
If not present, add it.

## Constraints
- Do NOT change function signatures beyond adding optional drive_url=None
- Do NOT break existing behavior when drive_url is None
- Keep import inside try block (lazy import)
- All exceptions must be caught and logged, never crash pipeline

## Test
After patching, run: python mail_pipeline/mail_pipeline.py --help
Should not crash. Then run: python matching_v2/notify_line.py --dry-run
"""

with open("mail_pipeline/SPEC_drive_patch.md", "w", encoding="utf-8") as f:
    f.write(spec)

tasks = """# TASKS_drive_patch.md

- [ ] Task 1: Patch mail_pipeline.py engineer branch - add Drive upload after skill_result
- [ ] Task 2: Patch mail_pipeline.py project branch - add Drive upload after skill_result
- [ ] Task 3: Patch register_engineer() - add drive_url param, write to Notion "Driveリンク"
- [ ] Task 4: Patch register_project() - add drive_url param, write to Notion "Driveリンク"
- [ ] Task 5: Patch notify_line.py build_project_message() - add 【添付ファイル】 section
- [ ] Task 6: Verify notify_line.py get_page_info() reads "Driveリンク" field
- [ ] Task 7: Run python mail_pipeline/mail_pipeline.py --help (should not crash)
"""

with open("mail_pipeline/TASKS_drive_patch.md", "w", encoding="utf-8") as f:
    f.write(tasks)

print("SPEC + TASKS written")
