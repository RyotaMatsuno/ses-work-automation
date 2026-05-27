import os

log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\logs\codex_sales_pipeline.log"
tasks_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\sales_pipeline\TASKS.md"
sp_dir = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\sales_pipeline"

if os.path.exists(log_path):
    with open(log_path, encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
    print(f"LOG_LINES:{len(lines)}", flush=True)
    for l in lines[-25:]:
        print(l, end='', flush=True)

print("\n=== TASKS.md ===", flush=True)
if os.path.exists(tasks_path):
    with open(tasks_path, encoding='utf-8', errors='replace') as f:
        print(f.read(), flush=True)

print(f"\n=== sales_pipeline/ files ===", flush=True)
if os.path.exists(sp_dir):
    print(os.listdir(sp_dir), flush=True)
