import subprocess
import sys

SRC = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(SRC, "rb") as f:
    raw = f.read()
text = raw.decode("utf-8")

idx = text.find("projects = fetch_all_pages(PROJECT_DB_ID")
nxt = text.find("\n", idx) + 1

dedup = (
    "\n    # dedup by project name (mail_pipeline may create duplicates)\n"
    "    _seen = set()\n"
    "    _deduped = []\n"
    "    for _p in projects:\n"
    "        _k = _text_prop(_p, PROP_PJNAME)\n"
    "        if _k and _k not in _seen:\n"
    "            _seen.add(_k)\n"
    "            _deduped.append(_p)\n"
    "    projects = _deduped\n"
)

new_text = text[:nxt] + dedup + text[nxt:]
with open(SRC, "wb") as f:
    f.write(new_text.encode("utf-8"))

result = subprocess.run(
    ["python", "-m", "py_compile", SRC], capture_output=True, text=True, encoding="utf-8", errors="replace"
)
sys.stdout.buffer.write(f"Syntax: {'OK' if result.returncode == 0 else result.stderr}\n".encode())
