import os

log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\logs\phase0_rerun.log"
result_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\logs\phase0_results.jsonl"

# ログをバイトで読む
if os.path.exists(log_path):
    with open(log_path, "rb") as f:
        data = f.read()
    text = data.decode("utf-8", errors="replace")
    lines = text.splitlines()
    print(f"log lines: {len(lines)}")
    for line in lines[-15:]:
        print(repr(line[:120]))
else:
    print("log not found")

# results
if os.path.exists(result_path):
    sz = os.path.getsize(result_path)
    with open(result_path, "r", encoding="utf-8") as f:
        cnt = sum(1 for l in f if l.strip())
    print(f"\nresults: {cnt} cases, {sz:,} bytes")
else:
    print("\nresults: not yet created")
