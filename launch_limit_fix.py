import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

codex = r"C:\Users\ma_py\AppData\Roaming\npm\codex.cmd"
cwd = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook"
log = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\codex_limit_fix.log"

instruction = (
    "line_query.py の format_project_result 関数と format_engineer_result 関数を修正してください。"
    "【変更内容】"
    "format_project_result: 表示を上位15件に制限する。"
    "ループ前に「display_projects = projects[:15]」を追加し、ループは display_projects を使う。"
    "ループ後、len(projects) > 15 の場合は lines.append(f'\\n他{len(projects)-15}件 | 粗利順上位15件を表示') を追加。"
    "format_engineer_result: 同様に上位10件に制限する。"
    "display_engineers = engineers[:10] を使い、超過時は lines.append(f'\\n他{len(engineers)-10}件 | 粗利順上位10件を表示') を追加。"
    "_limit_reply 関数は変更しない。"
    "変更後に python -m py_compile line_query.py を実行してエラーがないことを確認してください。"
)

with open(log, "w", encoding="utf-8") as lf:
    proc = subprocess.Popen(
        [codex, "exec", instruction, "--dangerously-bypass-approvals-and-sandbox"],
        cwd=cwd,
        stdout=lf,
        stderr=lf,
        creationflags=0x00000008,
    )

print(f"Codex PID: {proc.pid}  Log: {log}")
