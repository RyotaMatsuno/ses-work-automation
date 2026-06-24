import io
import re
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

paths = [
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py",
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py",
]
# 来源: → 連絡先:
for path in paths:
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    # \u6765\u6e90 = 来源 → \u9023\u7d61\u5148 = 連絡先
    src = src.replace('"\\u6765\\u6e90: {_esrc}"', '"\\u9023\\u7d61\\u5148: {_esrc}"')
    with open(path, "w", encoding="utf-8") as f:
        f.write(src)
    r = subprocess.run(["python", "-m", "py_compile", path], capture_output=True, text=True)
    fname = "/".join(path.split("\\")[-2:])
    print(f"{'✅' if r.returncode == 0 else '❌'} {fname}: 構文OK")

# デプロイ
print()
result = subprocess.run(
    [
        "cmd",
        "/c",
        "gcloud",
        "run",
        "deploy",
        "line-webhook",
        "--source",
        r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook",
        "--region=asia-northeast1",
        "--quiet",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    timeout=240,
)
m = re.search(r"line-webhook-\d{5}-\w+", result.stderr)
print(f"{'✅' if result.returncode == 0 else '❌'} デプロイ: {m.group(0) if m else '?'}")
