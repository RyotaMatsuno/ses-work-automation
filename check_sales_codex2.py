import time, os, subprocess

time.sleep(90)

log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\logs\codex_sales_pipeline.log"
tasks_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\sales_pipeline\TASKS.md"

if os.path.exists(log_path):
    with open(log_path, encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
    print(f"LOG_LINES:{len(lines)}", flush=True)
    print("=== 末尾30行 ===", flush=True)
    for l in lines[-30:]:
        print(l, end='', flush=True)

if os.path.exists(tasks_path):
    with open(tasks_path, encoding='utf-8', errors='replace') as f:
        print("\n=== TASKS.md ===", flush=True)
        print(f.read(), flush=True)

sp_files = os.listdir(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\sales_pipeline") if os.path.exists(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\sales_pipeline") else []
print(f"\n=== sales_pipeline/ ===\n{sp_files}", flush=True)
