from pathlib import Path

BASE = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")

TARGET_FILES = [
    "mail_pipeline.py",
    "matching_v2/matching_v2.py",
    "matching_v2/notify_line.py",
    "line_webhook/webhook_server.py",
    "local_server/command_server.py",
    "local_server/mcp_bridge.py",
    "mail_mcp/mail_server.py",
    "freee/freee_invoice_v2.py",
    "freee_auth/token_manager.py",
    "outreach_system/collect_targets.py",
    "outreach_system/outreach_main.py",
    "run_matching_and_notify.bat",
    "AGENTS.md",
]

output_lines = ["# Jobz コード全体ダンプ\n\n"]
found = []
not_found = []

for rel in TARGET_FILES:
    p = BASE / rel
    if p.exists():
        ext = p.suffix.lstrip(".")
        output_lines.append(f"## {rel}\n\n```{ext}\n")
        output_lines.append(p.read_text(encoding="utf-8", errors="replace"))
        output_lines.append("\n```\n\n")
        found.append(rel)
    else:
        not_found.append(rel)

# outreach_systemの中身を追加スキャン
for d in ["outreach_system", "sales_pipeline"]:
    dp = BASE / d
    if dp.exists():
        for f in dp.glob("*.py"):
            rel = f"{d}/{f.name}"
            if rel not in TARGET_FILES and rel not in found:
                ext = f.suffix.lstrip(".")
                output_lines.append(f"## {rel}\n\n```{ext}\n")
                output_lines.append(f.read_text(encoding="utf-8", errors="replace"))
                output_lines.append("\n```\n\n")
                found.append(rel)

out_path = BASE / "code_export.md"
out_path.write_text("".join(output_lines), encoding="utf-8")

print(f"出力完了: {out_path}")
print(f"収録ファイル数: {len(found)}")
print("収録:", found)
print("未発見:", not_found)
