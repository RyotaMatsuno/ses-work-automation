import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
nc_path = base / "matching_v3" / "notion_client.py"
text = nc_path.read_text(encoding="utf-8", errors="replace")

old = """{
            "filter": {
                "and": [
                    {"property": "登録日時", "date": {"on_or_after": since.isoformat()}},
                ]
            }
        }"""

new = """{
            "filter": {
                "and": [
                    {
                        "timestamp": "created_time",
                        "created_time": {"on_or_after": since.isoformat()}
                    },
                ]
            }
        }"""

if old in text:
    text_new = text.replace(old, new)
    nc_path.write_text(text_new, encoding="utf-8")
    print("OK: notion_client.py フィルター修正（登録日時→created_time）")
else:
    # インデントの違いを吸収して検索
    print("直接置換失敗。行番号で確認します")
    for i, l in enumerate(text.splitlines(), 1):
        if "登録日時" in l:
            print(f"  Line {i}: {repr(l)}")
