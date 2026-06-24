import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")

# ========== 2. config.py DEFAULT_STRUCTURER_MODEL を gpt-4o-mini に ==========
cfg_path = base / "matching_v3" / "config.py"
cfg_text = cfg_path.read_text(encoding="utf-8", errors="replace")
old_model = 'DEFAULT_STRUCTURER_MODEL = "claude-haiku-4-5-20251001"'
new_model = 'DEFAULT_STRUCTURER_MODEL = "gpt-4o-mini"  # [GPT切替] Anthropic月次上限のためGPTに変更'
if old_model in cfg_text:
    cfg_path.write_text(cfg_text.replace(old_model, new_model), encoding="utf-8")
    print("OK: config.py DEFAULT_STRUCTURER_MODEL → gpt-4o-mini")
else:
    print("NG: config.py 置換対象見つからない")

# ========== 3. matching_v3/cost_guard.py レート → gpt-4o-mini料金に更新 ==========
# gpt-4o-mini: input $0.15/1M, output $0.60/1M
cg_path = base / "matching_v3" / "cost_guard.py"
cg_text = cg_path.read_text(encoding="utf-8", errors="replace")
old_rates = "    HAIKU_INPUT_RATE = 1.0 / 1_000_000\n    HAIKU_OUTPUT_RATE = 5.0 / 1_000_000"
new_rates = (
    "    HAIKU_INPUT_RATE = 0.15 / 1_000_000   # gpt-4o-mini input rate\n"
    "    HAIKU_OUTPUT_RATE = 0.60 / 1_000_000  # gpt-4o-mini output rate"
)
if old_rates in cg_text:
    cg_path.write_text(cg_text.replace(old_rates, new_rates), encoding="utf-8")
    print("OK: cost_guard.py レート gpt-4o-mini料金に更新（input $0.15/M, output $0.60/M）")
else:
    print("NG: cost_guard.py レート置換対象見つからない")

# ========== 4. openai パッケージがインストール済みか確認 ==========
import subprocess

r = subprocess.run(
    ["python", "-c", "import openai; print('openai version:', openai.__version__)"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    cwd=str(base),
)
if r.returncode == 0:
    print(f"OK: {r.stdout.strip()}")
else:
    print("openai未インストール → pip install")
    r2 = subprocess.run(
        ["pip", "install", "openai", "--quiet", "--break-system-packages"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    print(f"pip install: rc={r2.returncode} {r2.stdout.strip()[:60]}")

# ========== 5. syntax確認 ==========
print("\n=== syntax確認 ===")
for f in ["matching_v3/structurer.py", "matching_v3/config.py", "matching_v3/cost_guard.py"]:
    r3 = subprocess.run(
        ["python", "-c", f"import py_compile; py_compile.compile('{f}', doraise=True); print('OK {f}')"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(base),
    )
    print(f"  {r3.stdout.strip() or 'NG: ' + r3.stderr.strip()[:80]}")
