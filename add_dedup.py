import subprocess
import sys

SRC = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(SRC, "rb") as f:
    raw = f.read()
text = raw.decode("utf-8", errors="replace")

# engineer_query の projects ループ前に重複排除を追加
old = (
    "    replies = []\n"
    "    for engineer in matched_engineers:\n"
    "        engineer_skills = _multi_select_prop(engineer, PROP_SKILL)"
)
new = (
    "    # dedup projects by name to handle duplicate registrations\n"
    "    seen_names = set()\n"
    "    deduped = []\n"
    "    for _p in projects:\n"
    "        _pname = _text_prop(_p, PROP_PJNAME)\n"
    "        if _pname and _pname not in seen_names:\n"
    "            seen_names.add(_pname)\n"
    "            deduped.append(_p)\n"
    "    projects = deduped\n"
    "    replies = []\n"
    "    for engineer in matched_engineers:\n"
    "        engineer_skills = _multi_select_prop(engineer, PROP_SKILL)"
)

if old in text:
    text = text.replace(old, new, 1)
    sys.stdout.buffer.write(b"dedup added\n")
else:
    sys.stdout.buffer.write(b"target not found\n")

with open(SRC, "w", encoding="utf-8") as f:
    f.write(text)

result = subprocess.run(
    ["python", "-m", "py_compile", SRC], capture_output=True, text=True, encoding="utf-8", errors="replace"
)
sys.stdout.buffer.write(f"Syntax: {'OK' if result.returncode == 0 else result.stderr}\n".encode())
