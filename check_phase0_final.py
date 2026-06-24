import json
import os

log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\logs\phase0_rerun2.log"
result_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\logs\phase0_results.jsonl"
out_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\phase0_status2.txt"

lines_to_write = []

if os.path.exists(log_path):
    with open(log_path, "rb") as f:
        data = f.read()
    text = data.decode("utf-8", errors="replace")
    log_lines = text.splitlines()
    lines_to_write.append(f"log lines: {len(log_lines)}")
    for line in log_lines[-20:]:
        safe = line.encode("ascii", errors="replace").decode("ascii")
        lines_to_write.append(f"  {safe[:200]}")
else:
    lines_to_write.append("log not found")

if os.path.exists(result_path):
    sz = os.path.getsize(result_path)
    total = match = review = ng = 0
    with open(result_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total += 1
            d = json.loads(line)
            for r in d.get("results", []):
                v = r.get("verdict", "").upper()
                if v == "MATCH":
                    match += 1
                elif v == "REVIEW":
                    review += 1
                elif v == "NG":
                    ng += 1
    lines_to_write.append(f"\nresults: {total} cases, {sz:,} bytes")
    total_pairs = match + review + ng
    lines_to_write.append(f"  MATCH:  {match} ({match / total_pairs * 100:.1f}%)" if total_pairs else "  MATCH: 0")
    lines_to_write.append(f"  REVIEW: {review} ({review / total_pairs * 100:.1f}%)" if total_pairs else "  REVIEW: 0")
    lines_to_write.append(f"  NG:     {ng} ({ng / total_pairs * 100:.1f}%)" if total_pairs else "  NG: 0")
else:
    lines_to_write.append("results: not yet created")

with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines_to_write))

print("written")
