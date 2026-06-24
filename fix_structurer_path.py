import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
st_path = base / "matching_v3" / "structurer.py"
text = st_path.read_text(encoding="utf-8", errors="replace")

# Line 11の sys.path.insert(0, "..") の前に matching_v3/ 自身を先頭に追加
old = '_sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), ".."))'
new = (
    "_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # matching_v3/ を最優先\n"
    '_sys.path.insert(1, _os.path.join(_os.path.dirname(__file__), ".."))'
)

if old in text:
    text_new = text.replace(old, new)
    st_path.write_text(text_new, encoding="utf-8")
    print("OK: structurer.py sys.path修正完了")
    # 修正後のLine 10-15確認
    for i, l in enumerate(text_new.splitlines()[8:16], 9):
        print(f"  {i}: {l}")
else:
    print("NG: 置換対象が見つからない")
    print(repr(text.splitlines()[10]))
