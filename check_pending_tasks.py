import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 未完了タスクに関係するファイルの存在確認
ses = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
checks = {
    "mail_attachment_importer": ses / "mail_attachment_importer",
    "propose_pipeline": ses / "propose_pipeline",
    "propose_pipeline/SPEC.md": ses / "propose_pipeline" / "SPEC.md",
    "propose_pipeline/TASKS.md": ses / "propose_pipeline" / "TASKS.md",
    "propose_pipeline/CLAUDE.md": ses / "propose_pipeline" / "CLAUDE.md",
    "outreach_system": ses / "outreach_system",
    "matching_v3": ses / "matching_v3",
    "cleanup_v2.py": ses / "cleanup_v2.py",
    "usage_tracker/cost_log.jsonl": ses / "usage_tracker" / "cost_log.jsonl",
}
for name, p in checks.items():
    exists = p.exists()
    if p.is_dir():
        files = list(p.iterdir()) if exists else []
        print(f"[{'DIR' if exists else '---'}] {name}  ({len(files)}files)")
    else:
        size = p.stat().st_size if exists else 0
        print(f"[{'OK ' if exists else '---'}] {name}  ({size:,}bytes)")

# propose_pipeline の中身
pp = ses / "propose_pipeline"
if pp.exists():
    print("\n--- propose_pipeline/ ---")
    for f in sorted(pp.iterdir()):
        print(f"  {f.name}  ({f.stat().st_size:,}b)")

# mail_attachment_importer の中身
mai = ses / "mail_attachment_importer"
if mai.exists():
    print("\n--- mail_attachment_importer/ ---")
    for f in sorted(mai.iterdir()):
        if f.is_file():
            print(f"  {f.name}  ({f.stat().st_size:,}b)")
