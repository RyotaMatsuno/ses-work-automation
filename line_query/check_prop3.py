import os
import sys

fpath = os.path.join(os.path.dirname(__file__), "line_query.py")
with open(fpath, "rb") as f:
    raw = f.read()
text = raw.decode("utf-8")

for func in ["def _select_prop", "def _number_prop", "def _multi_select_prop"]:
    idx = text.find(func)
    nxt = text.find("\ndef ", idx + 5)
    sys.stdout.buffer.write(text[idx:nxt].encode("utf-8"))
    sys.stdout.buffer.write(b"\n---\n")
