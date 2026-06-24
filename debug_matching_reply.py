import os
import sys

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook")
os.chdir(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook")

os.environ.setdefault("LINE_CHANNEL_SECRET", "dummy")
os.environ.setdefault("LINE_CHANNEL_ACCESS_TOKEN", "dummy")
os.environ.setdefault("NOTION_API_KEY", "dummy")
os.environ.setdefault("NOTION_ENGINEER_DB_ID", "dummy")
os.environ.setdefault("NOTION_PROJECT_DB_ID", "dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "dummy")

# build_matching_result_reply の中身を直接トレース
import json

result_path = os.path.join(os.path.dirname(__file__), "..", "matching_v2", "result.json")
print(f"result_path exists: {os.path.exists(result_path)}")
print(f"result_path resolved: {os.path.abspath(result_path)}")

with open(result_path, "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"type(data): {type(data)}")
print(f"len(data): {len(data)}")

items = data if isinstance(data, list) else data.get("projects", [])
print(f"len(items): {len(items)}")

project_count = 0
for item in items:
    candidates = item.get("candidates") or []
    if not candidates:
        continue
    project_name = item.get("project_name") or "（案件名なし）"
    print(f"案件: {project_name} / 候補: {len(candidates)}名")
    project_count += 1

print(f"project_count: {project_count}")
