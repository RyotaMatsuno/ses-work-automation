path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 備考 → 案件詳細 に置換（案件DB用のみ。エンジニアDB側は「備考（LINEメモ）」なので影響なし）
# register_project内の "備考" キーを "案件詳細" に
old = '"\\u5099\\u8003": {"rich_text": [{"text": {"content": note[:2000]}}]}'
new = '"\\u6848\\u4ef6\\u8a73\\u7d30": {"rich_text": [{"text": {"content": note[:2000]}}]}'
content = content.replace(old, new, 1)

# 期間登録を追加（register_projectのresの手前に）
old2 = '    res = requests.post("https://api.notion.com/v1/pages", headers=NOTION_HEADERS,\n                       json={"parent": {"database_id": NOTION_PROJECT_DB_ID}'
new2 = '    if info.get("period"): props["\\u671f\\u9593"] = {"rich_text": [{"text": {"content": info["period"]}}]}\n    res = requests.post("https://api.notion.com/v1/pages", headers=NOTION_HEADERS,\n                       json={"parent": {"database_id": NOTION_PROJECT_DB_ID}'
content = content.replace(old2, new2, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

# 確認
start = content.find("def register_project")
end = content.find("\ndef ", start + 1)
print(content[start:end])
