import os
from pathlib import Path

log_dir = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\logs")

# リセット対象（再実行で上書きされるファイル）
reset_files = [
    "phase0_processed.db",
    "phase0_results.jsonl",
    "structured.jsonl",
    "phase0_cost_log.jsonl",
]

for fname in reset_files:
    fpath = log_dir / fname
    if fpath.exists():
        os.remove(fpath)
        print(f"Deleted: {fname}")
    else:
        print(f"Not found (skip): {fname}")

print("\nReset complete. Ready for Phase 0 re-run.")
