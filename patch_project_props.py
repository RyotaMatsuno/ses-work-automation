path = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# register_project の props を正しいカラム名に修正
# + 案件詳細に本文を入れる + 転送文除去ロジックをclassify側のプロンプトに追加

old_register_project = '''def register_project(info, raw_text, sender):
    name = info.get("name") or "(no name)"
    note = f"[LINE auto-register: {sender}]\\n{info.get(\'note\', raw_text[:1500])}"
    props = {
        "\\u6848\\u4ef6\\u540d": {"title": [{"text": {"content": name}}]},
        "\\u30b9\\u30c6\\u30fc\\u30bf\\u30b9": {"select": {"name": "\\u52df\\u96c6\\u4e2d"}},
        "\\u5099\\u8003": {"rich_text": [{"text": {"content": note[:2000]}}]}
    }
    req = [s for s in info.get("required_skills", []) if s in VALID_SKILLS]
    opt = [s for s in info.get("optional_skills", []) if s in VALID_SKILLS]
    if req: props["\\u5fc5\\u8981\\u30b9\\u30ad\\u30eb"] = {"multi_select": [{"name": s} for s in req]}
    if opt: props["\\u5c1a\\u53ef\\u30b9\\u30ad\\u30eb"] = {"multi_select": [{"name": s} for s in opt]}
    if info.get("price"): props["\\u5358\\u4fa1\\uff08\\u4e07\\u5186\\uff09"] = {"number": info["price"]}
    if info.get("location"): props["\\u52e4\\u52d9\\u5730"] = {"rich_text": [{"text": {"content": info["location"]}}]}'''

new_register_project = '''def register_project(info, raw_text, sender):
    name = info.get("name") or "(no name)"
    detail = f"[LINE auto-register: {sender}]\\n{info.get(\'note\', raw_text[:1500])}"
    props = {
        "\\u6848\\u4ef6\\u540d": {"title": [{"text": {"content": name}}]},
        "\\u30b9\\u30c6\\u30fc\\u30bf\\u30b9": {"select": {"name": "\\u52df\\u96c6\\u4e2d"}},
        "\\u6848\\u4ef6\\u8a73\\u7d30": {"rich_text": [{"text": {"content": detail[:2000]}}]}
    }
    req = [s for s in info.get("required_skills", []) if s in VALID_SKILLS]
    opt = [s for s in info.get("optional_skills", []) if s in VALID_SKILLS]
    if req: props["\\u5fc5\\u8981\\u30b9\\u30ad\\u30eb"] = {"multi_select": [{"name": s} for s in req]}
    if opt: props["\\u5c1a\\u53ef\\u30b9\\u30ad\\u30eb"] = {"multi_select": [{"name": s} for s in opt]}
    price_val = normalize_price(info.get("price", 0))
    if price_val: props["\\u5358\\u4fa1\\uff08\\u4e07\\u5186\\uff09"] = {"number": price_val}
    if info.get("location"): props["\\u52e4\\u52d9\\u5730"] = {"rich_text": [{"text": {"content": info["location"]}}]}
    if info.get("period"): props["\\u671f\\u9593"] = {"rich_text": [{"text": {"content": info["period"]}}]}'''

content = content.replace(old_register_project, new_register_project, 1)

# classify_messageのsystemプロンプトに「転送文を無視して案件/人材情報だけ抽出」を追加
old_system = "system = 'SES business message classifier. Reply JSON only.\\nIMPORTANT: price field must be in 万円 unit as integer."
new_system = "system = 'SES business message classifier. Reply JSON only.\\nIMPORTANT: Ignore any forwarding remarks (e.g. \"これどうですか\", \"原さんどうですか\" etc.) and extract only the actual job/engineer information.\\nIMPORTANT: price field must be in 万円 unit as integer."

content = content.replace(old_system, new_system, 1)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("done")
