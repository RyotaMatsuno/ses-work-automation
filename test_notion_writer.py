
import os, sys, requests

base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
sys.path.insert(0, os.path.join(base, "mail_attachment_importer"))
os.chdir(base)

from dotenv import dotenv_values
env = dotenv_values(os.path.join(base, "config", ".env"))
for k, v in env.items():
    os.environ[k] = v

from notion_writer import write_engineer_to_notion

engineer = {
    "name": "テスト花子",
    "price": 60,
    "available_date": "2026-06-01",
    "experience_years": 3,
    "skills": ["Python", "Django", "AWS"]
}

print("Writing to Notion (dry-run check)...")
# notion_writerがdry_runオプションを持つか確認
import inspect
sig = inspect.signature(write_engineer_to_notion)
print("Signature:", sig)
