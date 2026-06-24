# -*- coding: utf-8 -*-
# line_webhook/line_query.pyのfetch_all_pages関数にタイムログを追加
path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

# fetch_all_pages関数の先頭にtimeログを追加
old = """def fetch_all_pages(db_id: str, filter_body: dict = None) -> list[dict]:
    results: list[dict] = []
    payload: dict[str, Any] = {"page_size": 100}"""

new = """def fetch_all_pages(db_id: str, filter_body: dict = None) -> list[dict]:
    import time as _time
    _t0 = _time.time()
    results: list[dict] = []
    payload: dict[str, Any] = {"page_size": 100}"""

if old in content:
    content = content.replace(old, new)
    # 関数末尾のbreakの後にログを追加
    old2 = """        if not data.get("has_more"):
            break
        payload["start_cursor"] = data.get("next_cursor")
    return results"""
    new2 = """        if not data.get("has_more"):
            break
        payload["start_cursor"] = data.get("next_cursor")
    _elapsed = _time.time() - _t0
    print(f"[fetch_all_pages] db={db_id[-8:]} count={len(results)} elapsed={_elapsed:.1f}s", flush=True)
    return results"""
    if old2 in content:
        content = content.replace(old2, new2)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("タイムログ追加完了", flush=True)
    else:
        print("old2 not found", flush=True)
else:
    print("old not found", flush=True)
