import sys
from pathlib import Path

from dotenv import dotenv_values

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
config = dotenv_values(base / "config" / ".env")

# OpenAI APIキー確認
openai_key = config.get("OPENAI_API_KEY", "")
print(f"OPENAI_API_KEY: {'SET(' + openai_key[:8] + '***)' if openai_key else 'NG(未設定)'}")

# structurer.py の _call_anthropic 関数全体確認
print("\n=== structurer.py _call_anthropic 全体 ===")
st = base / "matching_v3" / "structurer.py"
text = st.read_text(encoding="utf-8", errors="replace")
in_func = False
for i, l in enumerate(text.splitlines(), 1):
    if "def _call_anthropic" in l:
        in_func = True
    if in_func:
        print(f"  {i}: {l}")
        if in_func and i > 89 and l.strip().startswith("def ") and "_call_anthropic" not in l:
            break

# cost_guard.pyのget_model確認
print("\n=== matching_v3/cost_guard.py get_model ===")
mv3_cg = base / "matching_v3" / "cost_guard.py"
for i, l in enumerate(mv3_cg.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
    if "get_model" in l or "STRUCTURER_MODEL" in l or "haiku" in l.lower() or "gpt" in l.lower():
        print(f"  Line {i}: {l.strip()}")
