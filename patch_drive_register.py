
import re

path = "mail_pipeline/mail_pipeline.py"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

# バックアップ
with open(path + ".bak_drive", "w", encoding="utf-8") as f:
    f.write(src)

# === Patch 1: register_project() に drive_url 追加 ===
old_rp_sig = 'def register_project(info: dict, subject: str, sender: str, input_source: str = "", affiliation: str = "", raw_body: str = "") -> bool:'
new_rp_sig = 'def register_project(info: dict, subject: str, sender: str, input_source: str = "", affiliation: str = "", raw_body: str = "", drive_url: str = None) -> bool:'
src = src.replace(old_rp_sig, new_rp_sig)

# register_project内のadd_input_source_propertiesの後にDriveリンク追加
old_rp_body = '    add_input_source_properties(properties, PROJECT_DB, input_source, affiliation)\n    res = requests.post(\n        "https://api.notion.com/v1/pages",\n        headers=NOTION_HEADERS,\n        json={"parent": {"database_id": PROJECT_DB}, "properties": properties}\n    )\n    return res.status_code == 200'
new_rp_body = '    add_input_source_properties(properties, PROJECT_DB, input_source, affiliation)\n    if drive_url:\n        properties["Driveリンク"] = {"rich_text": [{"text": {"content": drive_url[:2000]}}]}\n    res = requests.post(\n        "https://api.notion.com/v1/pages",\n        headers=NOTION_HEADERS,\n        json={"parent": {"database_id": PROJECT_DB}, "properties": properties}\n    )\n    return res.status_code == 200'
src = src.replace(old_rp_body, new_rp_body)

# === Patch 2: register_engineer() に drive_url 追加 ===
old_re_sig = 'def register_engineer(info: dict, subject: str, sender: str, input_source: str = "", affiliation: str = "") -> tuple:'
new_re_sig = 'def register_engineer(info: dict, subject: str, sender: str, input_source: str = "", affiliation: str = "", drive_url: str = None) -> tuple:'
src = src.replace(old_re_sig, new_re_sig)

old_re_body = '    add_input_source_properties(properties, ENGINEER_DB, input_source, affiliation)\n    res = requests.post(\n        "https://api.notion.com/v1/pages",\n        headers=NOTION_HEADERS,\n        json={"parent": {"database_id": ENGINEER_DB}, "properties": properties}\n    )\n    if res.status_code == 200:\n        return True, res.json().get("id", "")'
new_re_body = '    add_input_source_properties(properties, ENGINEER_DB, input_source, affiliation)\n    if drive_url:\n        properties["Driveリンク"] = {"rich_text": [{"text": {"content": drive_url[:2000]}}]}\n    res = requests.post(\n        "https://api.notion.com/v1/pages",\n        headers=NOTION_HEADERS,\n        json={"parent": {"database_id": ENGINEER_DB}, "properties": properties}\n    )\n    if res.status_code == 200:\n        return True, res.json().get("id", "")'
src = src.replace(old_re_body, new_re_body)

print("Patch 1&2 (register funcs):", "OK" if "drive_url: str = None" in src else "FAILED")

with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("Saved.")
