
import os, sys

base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
sys.path.insert(0, os.path.join(base, "mail_attachment_importer"))
os.chdir(os.path.join(base, "mail_attachment_importer"))

from dotenv import dotenv_values
env = dotenv_values(os.path.join(base, "config", ".env"))
for k, v in env.items():
    os.environ[k] = v

from notion_writer import register_engineer, check_duplicate

engineer = {
    "name": "テスト花子_⑥動作確認",
    "price": 60,
    "available_date": "2026-06-01",
    "experience_years": 3,
    "skills": ["Python", "Django", "AWS"]
}

# 重複チェック
dup = check_duplicate(engineer["name"])
print("Duplicate:", dup)

if not dup:
    result = register_engineer(engineer, source="line_test")
    print("Register result:", result)
else:
    print("Already exists, skipping")
