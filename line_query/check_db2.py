import sys

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query")
from line_query import ENGINEER_DB_ID, fetch_all_pages

pages = fetch_all_pages(ENGINEER_DB_ID)

# 名前と全プロパティのキーを確認（最初の3件）
for p in pages[:3]:
    props = p.get("properties", {})
    name_arr = props.get("名前", {}).get("title", [])
    name = name_arr[0]["plain_text"] if name_arr else "(no name)"
    print(f"\n=== {name} ===")
    for k, v in props.items():
        vtype = v.get("type")
        val = ""
        if vtype == "rich_text":
            arr = v.get("rich_text", [])
            val = arr[0]["plain_text"] if arr else ""
        elif vtype == "select":
            sel = v.get("select")
            val = sel["name"] if sel else ""
        elif vtype == "number":
            val = str(v.get("number", ""))
        elif vtype == "multi_select":
            val = ", ".join(x["name"] for x in v.get("multi_select", []))
        if val:
            print(f"  {k}: {val[:60]}")
