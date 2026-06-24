import sys

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query")
from line_query import ENGINEER_DB_ID, _normalize_initial, _text_prop, fetch_all_pages

pages = fetch_all_pages(ENGINEER_DB_ID)

# H.SレコードのDB内容を全部見る
for p in pages:
    name = _text_prop(p, "名前")
    if _normalize_initial(name) == "HS":
        print(f"=== {name} ===")
        props = p.get("properties", {})
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
            elif vtype == "email":
                val = v.get("email") or ""
            elif vtype == "phone_number":
                val = v.get("phone_number") or ""
            elif vtype == "url":
                val = v.get("url") or ""
            elif vtype == "date":
                d = v.get("date")
                val = d["start"] if d else ""
            if val:
                print(f"  [{k}]: {val[:120]}")
