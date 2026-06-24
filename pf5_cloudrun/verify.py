import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")

# 1. syntax確認
print("=== syntax確認 ===")
r = subprocess.run(
    [
        "python",
        "-c",
        "import py_compile; py_compile.compile('line_webhook/webhook_server.py', doraise=True); py_compile.compile('line_webhook/skill_extractor.py', doraise=True); print('ALL OK')",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    cwd=str(base),
)
print(f"stdout: {r.stdout.strip()}")
print(f"stderr: {r.stderr.strip()}")
print(f"returncode: {r.returncode}")

# 2. LLM_KILL追加箇所の確認
print("\n=== webhook_server.py LLM_KILL追加箇所 ===")
wh = base / "line_webhook" / "webhook_server.py"
lines = wh.read_text(encoding="utf-8", errors="replace").splitlines()
for i, l in enumerate(lines, 1):
    if "LLM_KILL" in l or "llm_kill" in l.lower():
        print(f"  Line {i}: {l}")

print("\n=== skill_extractor.py LLM_KILL追加箇所 ===")
se = base / "line_webhook" / "skill_extractor.py"
se_lines = se.read_text(encoding="utf-8", errors="replace").splitlines()
for i, l in enumerate(se_lines, 1):
    if "LLM_KILL" in l or "llm_kill" in l.lower():
        print(f"  Line {i}: {l}")
