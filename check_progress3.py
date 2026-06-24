import os

log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\logs\phase0_rerun.log"
result_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\logs\phase0_results.jsonl"
out_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\phase0_status.txt"

lines_to_write = []

if os.path.exists(log_path):
    with open(log_path, "rb") as f:
        data = f.read()
    text = data.decode("utf-8", errors="replace")
    log_lines = text.splitlines()
    lines_to_write.append(f"log lines: {len(log_lines)}")
    for line in log_lines[-15:]:
        safe = line.encode("ascii", errors="replace").decode("ascii")
        lines_to_write.append(f"  {safe[:150]}")
else:
    lines_to_write.append("log not found")

if os.path.exists(result_path):
    sz = os.path.getsize(result_path)
    with open(result_path, "r", encoding="utf-8") as f:
        cnt = sum(1 for l in f if l.strip())
    lines_to_write.append(f"results: {cnt} cases, {sz:,} bytes")
else:
    lines_to_write.append("results: not yet created")

with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines_to_write))

print("written to phase0_status.txt")
