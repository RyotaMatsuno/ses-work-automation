import sys

sys.stdout.reconfigure(encoding="utf-8")

IMP = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_attachment_importer"

# ai_extractor.pyのSKILL_OPTIONS現状確認
with open(IMP + r"\ai_extractor.py", encoding="utf-8") as f:
    ai = f.read()

# notion_writer.pyのcheck_duplicate現状確認
with open(IMP + r"\notion_writer.py", encoding="utf-8") as f:
    nw = f.read()

# processed_ids.jsonのサイズ確認
import json
import os

pid_path = IMP + r"\processed_ids.json"
size = os.path.getsize(pid_path)
with open(pid_path, encoding="utf-8") as f:
    pids = json.load(f)
print(f"processed_ids size: {size} bytes")
for k, v in pids.items():
    print(f"  {k}: {len(v)}件")

# SKILL_OPTIONS現状
import re

m = re.search(r"SKILL_OPTIONS = \[(.*?)\]", ai, re.DOTALL)
if m:
    print(f"\n現在のスキル数: {ai.count(chr(34), m.start(), m.end()) // 2}種")
