import sys

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query")
from line_query import ENGINEER_DB_ID, fetch_all_pages

pages = fetch_all_pages(ENGINEER_DB_ID)
print(f"Total engineers: {len(pages)}")

# イニシャルと最寄り駅を全件表示
for p in pages:
    props = p.get("properties", {})
    name_arr = props.get("名前", {}).get("title", [])
    name = name_arr[0]["plain_text"] if name_arr else ""
    ini_arr = props.get("イニシャル", {}).get("rich_text", [])
    ini = ini_arr[0]["plain_text"] if ini_arr else ""
    sta_arr = props.get("最寄り駅", {}).get("rich_text", [])
    sta = sta_arr[0]["plain_text"] if sta_arr else ""
    if ini or sta:
        print(f"  {repr(ini):10} | {repr(sta):20} | {name}")
