path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# process_message内の返信文でnormalize_priceを使うように修正
old = """    if msg_type == "engineer":
        success, _ = register_engineer(info, text, sender)
        name = info.get("name", "(no name)")
        skills_str = ", ".join(info.get("skills", [])) or "N/A"
        price = info.get("price", 0)"""

new = """    if msg_type == "engineer":
        success, _ = register_engineer(info, text, sender)
        name = info.get("name", "(no name)")
        skills_str = ", ".join(info.get("skills", [])) or "N/A"
        price = normalize_price(info.get("price", 0))"""

content = content.replace(old, new, 1)
with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("done")
print(content[content.find('if msg_type == "engineer"') : content.find('if msg_type == "engineer"') + 300])
