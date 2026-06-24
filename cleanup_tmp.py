import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")

tmp_files = [
    "admin_fix_outlook_tasks.bat",
    "admin_fix_outlook.ps1",
    "run_as_admin.bat",
    "SES_Outlook_9h_new.xml",
    "SES_Outlook_13h_new.xml",
    "SES_Outlook_18h_new.xml",
    "audit_1.py",
    "audit_2.py",
    "audit_3.py",
    "audit_4.py",
    "audit_5.py",
    "audit_tasks.py",
    "check_cleanup.py",
    "check_engineer_dist.py",
    "check_handoff.py",
    "check_handoff2.py",
    "check_handoff3.py",
    "check_handoff4.py",
    "check_handoff5.py",
    "check_smtp.py",
    "check_smtp2.py",
    "check_webhook.py",
    "pre_fix_check.py",
    "apply_fixes.py",
    "update_schedulers.py",
    "update_schedulers2.py",
    "fix_outlook_tasks.py",
    "fix_outlook2.py",
    "fix_outlook_xml.py",
    "fix_outlook_xml2.py",
    "fix_outlook_xml3.py",
    "fix_outlook_xml4.py",
    "debug_del.py",
    "verify_ps.py",
    "prepare_admin_fix.py",
    "regen_bat.py",
    "regen_bat2.py",
    "get_short_path.py",
    "gen_ps1.py",
    "verify_admin.py",
    "verify_schedulers.py",
    "final_verify.py",
    "final_verify2.py",
    "run_pipeline_wd.bat",
    "run_importer_wd.bat",
    "run_daily_wd.bat",
]
deleted = 0
for f in tmp_files:
    p = base / f
    if p.exists():
        p.unlink()
        deleted += 1
print(f"削除: {deleted}件")
