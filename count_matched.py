import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import importlib.util

spec = importlib.util.spec_from_file_location(
    "lq", r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
)
lq = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lq)

from dotenv import dotenv_values

cfg = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = cfg.get("NOTION_API_KEY") or cfg.get("NOTION_TOKEN")
headers = {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

filt = {
    "and": [
        {"property": lq.PROP_RATE, "number": {"greater_than_or_equal_to": 75}},
        {"property": lq.PROP_STATUS, "select": {"equals": lq.VAL_RECRUITING}},
    ]
}
projects = lq.fetch_all_pages(lq.PROJECT_DB_ID, filter_body=filt)

eng_skills = ["Java", "JavaScript", "SQL Server", "Oracle", "Spring", "C#"]
eng_rate = 70.0

with_skill = []
without_skill_high_gross = []

for p in projects:
    req_sk = lq._multi_select_prop(p, lq.PROP_REQSK)
    budget = lq._number_prop(p, lq.PROP_RATE)
    gross = lq.calc_gross_profit(budget, eng_rate)
    sm = lq.skill_match(req_sk, eng_skills)

    if req_sk and sm and gross >= 5:
        with_skill.append({"name": lq._text_prop(p, lq.PROP_PJNAME), "gross": gross, "req": req_sk})
    elif not req_sk and gross >= 10:
        without_skill_high_gross.append({"name": lq._text_prop(p, lq.PROP_PJNAME), "gross": gross})

sys.stdout.buffer.write(f"Skill-matched: {len(with_skill)}\n".encode("utf-8"))
sys.stdout.buffer.write(f"No-skill high-gross: {len(without_skill_high_gross)}\n".encode("utf-8"))
sys.stdout.buffer.write(b"\nTop skill-matched:\n")
for m in sorted(with_skill, key=lambda x: -x["gross"])[:10]:
    sys.stdout.buffer.write(f"  gross={m['gross']:.0f} {m['name'][:25]} req={m['req']}\n".encode("utf-8"))
