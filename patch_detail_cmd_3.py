# -*- coding: utf-8 -*-
# 変更3: engineer_query でマッチ結果を _LAST_RESULTS にキャッシュ
# 変更4: handle_line_query に「詳細 N」パターン検出を追加

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

# 変更3: engineer_query の matched.sort後にキャッシュ保存を追加
old3 = """        matched.sort(key=lambda x: x["gross_profit"], reverse=True)
        replies.append(format_project_result(engineer, matched))
    return "\\n\\n".join(replies)"""

new3 = """        matched.sort(key=lambda x: x["gross_profit"], reverse=True)
        # 詳細照会用にキャッシュ保存
        cache_key = f"{initial}_{station}"
        _LAST_RESULTS[cache_key] = [item["page"] for item in matched]
        replies.append(format_project_result(engineer, matched))
    return "\\n\\n".join(replies)"""

if old3 in content:
    content = content.replace(old3, new3)
    print("変更3 OK", flush=True)
else:
    print("変更3 MISS", flush=True)

# 変更4: handle_line_query に詳細コマンド検出を追加
old4 = """def handle_line_query(text: str) -> str | None:
    if not text or not text.strip():
        return None
    if len(text.strip()) > 100:
        return None
    try:
        query_type, params = classify_query(text)"""

new4 = """def handle_line_query(text: str) -> str | None:
    if not text or not text.strip():
        return None
    # 詳細コマンド: 「詳細 ①」「詳細 6」など
    if text.strip().startswith("詳細"):
        return detail_query(text.strip())
    if len(text.strip()) > 100:
        return None
    try:
        query_type, params = classify_query(text)"""

if old4 in content:
    content = content.replace(old4, new4)
    print("変更4 OK", flush=True)
else:
    print("変更4 MISS", flush=True)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("書き込み完了", flush=True)
