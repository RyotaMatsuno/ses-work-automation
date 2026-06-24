import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

mp = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\mail_pipeline.py")
with open(mp, encoding="utf-8", errors="replace") as f:
    lines = f.readlines()

# Fix1: 定数確認
print("=== [Fix1] 定数 ===")
for i, l in enumerate(lines[:80], 1):
    if any(k in l for k in ["FETCH_LIMIT", "PROCESS_LIMIT", "DAILY_COST"]):
        print(f"L{i}: {l.rstrip()}")

# Fix2: processed_ids 上限ロジック
print("\n=== [Fix2] processed_ids 上限ロジック ===")
for i, l in enumerate(lines, 1):
    if "10000" in l or "ids_list" in l:
        print(f"L{i}: {l.rstrip()}")

# Fix3: finally の存在確認
print("\n=== [Fix3] finally 節 ===")
for i, l in enumerate(lines, 1):
    if "finally" in l.lower():
        # 前後5行
        start = max(0, i - 3)
        end = min(len(lines), i + 5)
        for j, ll in enumerate(lines[start:end], start + 1):
            print(f"L{j}: {ll.rstrip()}")
        print("---")

# Fix4: get_today_cost_usd と call_claude 先頭のガード
print("\n=== [Fix4] get_today_cost_usd ===")
in_func = False
for i, l in enumerate(lines, 1):
    if "def get_today_cost_usd" in l:
        in_func = True
    if in_func:
        print(f"L{i}: {l.rstrip()}")
        if i > 1 and l.strip() == "" and in_func:
            # 関数終了（空行2連続判定は難しいので20行で打ち切り）
            pass
        if in_func and i > (next((j for j, ll in enumerate(lines, 1) if "def get_today_cost_usd" in ll), 0) + 20):
            break

print("\n=== [Fix4] call_claude 先頭ガード ===")
in_claude = False
for i, l in enumerate(lines, 1):
    if "def call_claude" in l:
        in_claude = True
    if in_claude:
        print(f"L{i}: {l.rstrip()}")
        if in_claude and i > (next((j for j, ll in enumerate(lines, 1) if "def call_claude" in ll), 0) + 12):
            break

# Fix1: SINCE フィルタ確認
print("\n=== [Fix1] SINCE フィルタ ===")
for i, l in enumerate(lines, 1):
    if "SINCE" in l or "since" in l.lower() and "days" in l.lower():
        print(f"L{i}: {l.rstrip()}")
