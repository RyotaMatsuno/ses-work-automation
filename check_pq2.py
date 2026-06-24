import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

# project_queryの稼働状況チェック部分を確認
idx = src.find("def project_query")
print(src[idx : idx + 900])
