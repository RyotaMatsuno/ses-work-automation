import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook"
out = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\lq_detail.txt"

with open(base + r"\line_query.py", encoding="utf-8", errors="replace") as f:
    content = f.read()

lines = content.split("\n")


def extract_fn(name):
    start = next((i for i, l in enumerate(lines) if f"def {name}" in l), None)
    if start is None:
        return f"{name}: not found"
    end = start + 1
    while end < len(lines):
        if lines[end].startswith("def ") and end > start + 2:
            break
        end += 1
    return f"=== {name} (L{start + 1}) ===\n" + "\n".join(lines[start : min(start + 60, end)])


result = "\n\n".join(
    [
        extract_fn("classify_query"),
        extract_fn("engineer_query"),
        extract_fn("project_query"),
    ]
)

with open(out, "w", encoding="utf-8") as f:
    f.write(result)
print(result[:5000])
