import glob
import os
import shutil

ses_work = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
archive_dir = os.path.join(ses_work, "_archive_tmp")
os.makedirs(archive_dir, exist_ok=True)

# Move patterns: temporary/debug/one-off scripts
patterns = [
    "check_*.py",
    "tmp_*.py",
    "show_*.py",
    "read_*.py",
    "patch_*.py",
    "fix_*.py",
    "find_*.py",
    "wait_*.py",
    "run_codex_*.py",
    "write_*.py",
    "verify_*.py",
    "debug_*.py",
    "test_*.py",
    "smoke_*.py",
    "run_dry*.py",
    "run_notify*.py",
    "run_pipeline_*.py",
    "launch_cleanup*.py",
    "launch_pipeline*.py",
    "launch_skill*.py",
    "add_*.py",
    "delete_*.py",
    "export_*.py",
    "memo_*.py",
    "investigate_*.py",
    "diagnose_*.py",
    "collect_subjects.py",
    "consult_arch.py",
    "cost_*.py",
    "count_*.py",
    "dump_*.py",
    "mask_secrets.py",
    "build_importer*.py",
    "build_targets.py",
    "set_railway_env*.py",
    "redeploy_railway.py",
    "install_*.py",
    "register_*.py",
    "setup_*.py",
    "restore_and_fix.py",
    "save_ceo_v8.py",
    "simplify_status_cmd.py",
    "to_b64.py",
    "update_*.py",
    "wall_hitting.py",
    "migrate_to_sheets.py",
    "import_emails_*.py",
    "cf_login*.py",
    "cf_login*.log",
    # Log files
    "*.log",
    # One-off output files
    "build_importer_out.txt",
    "collect_*.txt",
    "db_check.txt",
    "debug_lines.txt",
    "diagnosis.txt",
    "dryrun_out.txt",
    "dry_run_*.txt",
    "model_*.txt",
    "notify_*.txt",
    "schtasks_all.txt",
    "test_out.txt",
    "check_line498.txt",
]

# Files/dirs to KEEP (never move)
keep = {
    "matching_v2",
    "mail_pipeline",
    "mail_mcp",
    "local_server",
    "line_webhook",
    "freee",
    "freee_auth",
    "outreach_system",
    "sales_pipeline",
    "mail_attachment_importer",
    "attachment_importer",
    "double_check",
    "usage_tracker",
    "config",
    "context",
    "contract",
    "clients",
    "engineers",
    "gmail",
    "gcal",
    "logs",
    "notion",
    "mcp_data",
    "outlook",
    "project_files",
    "reply_parser",
    "reports",
    "sheets",
    "skills",
    "skill_reader",
    "templates",
    "work",
    "_archive_tmp",
    ".git",
    ".github",
    ".gitignore",
    "AGENTS.md",
    "CLAUDE.md",
    "HANDOFF.md",
    "analyze_final.py",
    "matching.py",
    "matching_utf8.py",
    "git_push.bat",
    "run_matching_and_notify.bat",
    "daily_report.py",
    "run_daily_report.bat",
    "ses-work-automation-170e12155a49.json",
    "google_credentials.json",
    "active_result.json",
    "result_pipeline.json",
    "__pycache__",
    # SPEC/TASKS files (important)
    "SPEC_daily_report.md",
    "SPEC_git_cleanup.md",
    "from_switch_spec",
    "input_label_spec",
    "mail_mime_spec",
    "pipeline_notify_fix",
    "pipeline_v1",
    "propose_pipeline",
    "PFIX_CLAUDE.md",
    "PFIX_SPEC.md",
    "PFIX_TASKS.md",
    # Scripts that are part of core systems
    "auto_invoice_and_update.py",
    "run_matching_bg.bat",
    "run_matching_bg.py",
    "launch_matching_bg.py",
    "audit.py",
    "audit_engineers.py",
    "archive_engineers.py",
    "exclude_engineers.py",
    "cleanup_v2.py",
    # The patching script we just used
    "patch_prefilter.py",
    "check_matching_scope.py",
    "count_db.py",
}

moved = 0
skipped = 0
for pattern in patterns:
    for filepath in glob.glob(os.path.join(ses_work, pattern)):
        basename = os.path.basename(filepath)
        if basename in keep:
            skipped += 1
            continue
        if os.path.isdir(filepath):
            continue
        try:
            dest = os.path.join(archive_dir, basename)
            if os.path.exists(dest):
                # Append number to avoid overwrite
                name, ext = os.path.splitext(basename)
                i = 1
                while os.path.exists(dest):
                    dest = os.path.join(archive_dir, f"{name}_{i}{ext}")
                    i += 1
            shutil.move(filepath, dest)
            moved += 1
        except Exception as e:
            print(f"ERROR moving {basename}: {e}")

print(f"Moved: {moved}, Skipped: {skipped}")

# Also move stray JSON files that are temp outputs
json_temps = [
    "all_sheets.json",
    "bak_terra.json",
    "classification_result.json",
    "config_source.json",
    "excel_dump.json",
    "ft_all.json",
    "ft_check.json",
    "freee_invoices.json",
    "missing_prices.json",
    "names.json",
    "notion_props.json",
    "notion_status.json",
    "nyukin_v2.json",
    "nyukin_yosoku.json",
    "price_bugs.json",
    "scan_result.json",
    "mail_subjects_sample.json",
]
for jf in json_temps:
    fp = os.path.join(ses_work, jf)
    if os.path.exists(fp) and jf not in keep:
        try:
            shutil.move(fp, os.path.join(archive_dir, jf))
            moved += 1
        except:
            pass

# Move stray .md files that are one-off specs
md_temps = [
    "CLAUDE_wall.md",
    "SPEC_wall.md",
    "SPEC_wall_v2.md",
    "SPEC_input_source.md",
    "TASKS_input_source.md",
    "TASKS_wall.md",
    "TASKS_wall_v2.md",
    "handover_20260501.md",
]
for mf in md_temps:
    fp = os.path.join(ses_work, mf)
    if os.path.exists(fp):
        try:
            shutil.move(fp, os.path.join(archive_dir, mf))
            moved += 1
        except:
            pass

# Move misc one-off files
misc = [
    "claude_desktop_config_new.json",
    "spreadsheet_id.txt",
    "ngrok_screen.png",
    "cloudflared_login.bat",
    "install_cursor.bat",
    "restart_claude.bat",
    "diagnose_claude.bat",
]
for mf in misc:
    fp = os.path.join(ses_work, mf)
    if os.path.exists(fp):
        try:
            shutil.move(fp, os.path.join(archive_dir, mf))
            moved += 1
        except:
            pass

print(f"Total moved (incl json/md/misc): {moved}")
