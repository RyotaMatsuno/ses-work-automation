import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")

# matching_v3の昨日のログからAPI呼び出し回数を確認
log = base / "matching_v3" / "logs" / "matching_v3_20260604.log"
lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
api_calls = [l for l in lines if "HTTP Request: POST" in l and "anthropic" in l]
print(f"昨日(06/04)のAPI呼び出し: {len(api_calls)}回")
# 時間帯分布
from collections import Counter

hours = Counter(l[11:13] for l in api_calls if len(l) > 13)
for h, c in sorted(hours.items()):
    print(f"  {h}時: {c}回")

# structurer.py のモデル設定確認
print("\n=== 現在のモデル設定 ===")
st = base / "matching_v3" / "structurer.py"
for i, l in enumerate(st.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
    if any(k in l for k in ["model", "claude", "gemini", "gpt", "haiku", "flash"]):
        stripped = l.strip()
        if stripped and not stripped.startswith("#"):
            print(f"  Line {i}: {stripped}")

# config.py のDEFAULT_STRUCTURER_MODEL
print("\n=== DEFAULT_STRUCTURER_MODEL ===")
cfg = base / "matching_v3" / "config.py"
for i, l in enumerate(cfg.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
    if "MODEL" in l or "model" in l.lower():
        print(f"  Line {i}: {l.strip()}")
