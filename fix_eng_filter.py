import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
nc_path = base / "matching_v3" / "notion_client.py"
text = nc_path.read_text(encoding="utf-8", errors="replace")

# 修正: 提案対象フラグを除去 + since をISO date文字列（timezone不要）に変更
old = """    def get_active_engineers(self) -> list[dict[str, Any]]:
        since = (datetime.now(JST) - timedelta(weeks=3)).isoformat()
        payload = {
            "filter": {
                "and": [
                    {"timestamp": "last_edited_time", "last_edited_time": {"on_or_after": since}},
                    {"property": "提案対象フラグ", "checkbox": {"equals": True}},
                    {
                        "or": [
                            {"property": "稼働状況", "select": {"equals": "稼働可能"}},
                            {"property": "稼働状況", "select": {"equals": "稼働中"}},
                            {"property": "稼働状況", "select": {"equals": "調整中"}},
                        ]
                    },
                ]
            }
        }"""

new = """    def get_active_engineers(self) -> list[dict[str, Any]]:
        since = (datetime.now(JST) - timedelta(weeks=3)).date().isoformat()
        payload = {
            "filter": {
                "and": [
                    {"timestamp": "last_edited_time", "last_edited_time": {"on_or_after": since}},
                    {
                        "or": [
                            {"property": "稼働状況", "select": {"equals": "稼働可能"}},
                            {"property": "稼働状況", "select": {"equals": "稼働中"}},
                            {"property": "稼働状況", "select": {"equals": "調整中"}},
                        ]
                    },
                ]
            }
        }"""

if old in text:
    text_new = text.replace(old, new)
    nc_path.write_text(text_new, encoding="utf-8")
    print("OK: get_active_engineers 修正（提案対象フラグ除去 + since.date()化）")
else:
    print("NG: 置換対象見つからない")
    for i, l in enumerate(text.splitlines(), 1):
        if "提案対象フラグ" in l or "def get_active_engineers" in l:
            print(f"  Line {i}: {repr(l)}")
