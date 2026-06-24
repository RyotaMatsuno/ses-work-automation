import subprocess

SRC = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(SRC) as f:
    text = f.read()

# fetch後の行を探す
idx = text.find("projects = fetch_all_pages(PROJECT_DB_ID")
nxt_line_end = text.find("\n", idx) + 1
print("fetch line:", repr(text[idx:nxt_line_end]))

# その直後にdedup挿入
dedup = (
    "\n    # dedup by project name (mail_pipeline may create duplicates)\n"
    "    _seen = set()\n"
    "    projects = [p for p in projects\n"
    "                if _text_prop(p, PROP_PJNAME) not in _seen\n"
    "                and not _seen.add(_text_prop(p, PROP_PJNAME))]\n"
)
text = text[:nxt_line_end] + dedup + text[nxt_line_end:]

with open(SRC, "w", encoding="utf-8") as f:
    f.write(text)

result = subprocess.run(
    ["python", "-m", "py_compile", SRC], capture_output=True, text=True, encoding="utf-8", errors="replace"
)
print("Syntax:", "OK" if result.returncode == 0 else result.stderr)
