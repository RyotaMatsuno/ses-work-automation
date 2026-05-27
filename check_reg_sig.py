
import os, sys, inspect

base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
sys.path.insert(0, os.path.join(base, "mail_attachment_importer"))

from dotenv import dotenv_values
env = dotenv_values(os.path.join(base, "config", ".env"))
for k, v in env.items():
    os.environ[k] = v

from notion_writer import register_engineer
print("Signature:", inspect.signature(register_engineer))
