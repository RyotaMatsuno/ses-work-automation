filepath = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\notify_line.py"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

old = '''def get_page_info(page_id, headers, page_type):
    if not page_id:
        return empty_page_info(page_type)

    response = requests.get('''

new = '''def get_page_info(page_id, headers, page_type):
    if not page_id:
        return empty_page_info(page_type)
    if os.environ.get("SKIP_NOTION_FETCH") == "1":
        return empty_page_info(page_type)

    response = requests.get('''

if old in content:
    content = content.replace(old, new)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print("Patch3 applied.")
else:
    print("Pattern not found!")
    # デバッグ: 前後を表示
    idx = content.find("def get_page_info")
    print(repr(content[idx:idx+200]))
