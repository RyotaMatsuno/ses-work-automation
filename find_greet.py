import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

# greet_patternsの実際の末尾を探す
idx = src.find("greet_patterns = [")
block = src[idx : idx + 2000]
print(block[:1000])
