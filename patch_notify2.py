filepath = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\notify_line.py"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# dry-run時はNotionを呼ばないようにget_assigneeをショートサーキット
# get_assignee関数の先頭にdry_run判定を追加するのではなく、
# result.jsonのproject/engineer情報を直接使い、Notion呼び出しをスキップする方針で
# get_assignee()の先頭にenv変数チェックを追加（DRY_RUN=1の場合はデフォルト返す）

old_get_assignee = '''def get_assignee(page_id: str, headers: dict) -> str:
    """NotionページのIDから担当者を取得。未設定・共通はデフォルト'松野'を返す。"""
    if not page_id:
        return DEFAULT_ASSIGNEE

    response = requests.get('''

new_get_assignee = '''def get_assignee(page_id: str, headers: dict) -> str:
    """NotionページのIDから担当者を取得。未設定・共通はデフォルト'松野'を返す。"""
    if not page_id:
        return DEFAULT_ASSIGNEE
    if os.environ.get("SKIP_NOTION_FETCH") == "1":
        return DEFAULT_ASSIGNEE

    response = requests.get('''

content = content.replace(old_get_assignee, new_get_assignee)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("Patch2 applied.")
