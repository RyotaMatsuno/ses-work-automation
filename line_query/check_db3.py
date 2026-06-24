import sys

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query")
from line_query import ENGINEER_DB_ID, fetch_all_pages

pages = fetch_all_pages(ENGINEER_DB_ID)
print(f"Total: {len(pages)}\n")
print("=== 全員の名前・備考（LINEメモ）先頭100文字 ===")
for p in pages:
    props = p.get("properties", {})
    name_arr = props.get("名前", {}).get("title", [])
    name = name_arr[0]["plain_text"] if name_arr else ""
    memo_arr = props.get("備考（LINEメモ）", {}).get("rich_text", [])
    memo = memo_arr[0]["plain_text"][:80] if memo_arr else ""
    ini_arr = props.get("イニシャル", {}).get("rich_text", [])
    ini = ini_arr[0]["plain_text"] if ini_arr else ""
    sta_arr = props.get("最寄り駅", {}).get("rich_text", [])
    sta = sta_arr[0]["plain_text"] if sta_arr else ""
    print(f"  名前:{repr(name):20} イニシャル:{repr(ini):8} 最寄:{repr(sta):15} メモ:{memo[:60]}")
