import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import importlib.util

from dotenv import dotenv_values

spec = importlib.util.spec_from_file_location(
    "lq", r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
)
lq = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lq)

# テスト: budget>=75 AND status=募集中 の案件件数
cfg = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = cfg.get("NOTION_API_KEY") or cfg.get("NOTION_TOKEN")
headers = {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

prj_filter = {
    "and": [
        {"property": lq.PROP_RATE, "number": {"greater_than_or_equal_to": 75}},
        {"property": lq.PROP_STATUS, "select": {"equals": lq.VAL_RECRUITING}},
    ]
}

sys.stdout.buffer.write(f"Filter: budget>={75}, status={lq.VAL_RECRUITING!r}\n".encode("utf-8"))

projects = lq.fetch_all_pages(lq.PROJECT_DB_ID, filter_body=prj_filter)
sys.stdout.buffer.write(f"Projects after filter: {len(projects)}\n".encode("utf-8"))

# H.Sのスキルでさらにフィルタ
eng_skills = ["Java", "JavaScript", "SQL Server", "Oracle", "Spring", "C#"]
eng_rate = 70.0

matched = []
for p in projects:
    req_sk = lq._multi_select_prop(p, lq.PROP_REQSK)
    budget = lq._number_prop(p, lq.PROP_RATE)
    gross = lq.calc_gross_profit(budget, eng_rate)
    thresh = lq._gross_threshold(lq._select_prop(p, lq.PROP_ASSIGNEE))
    sm = lq.skill_match(req_sk, eng_skills)
    if sm and gross >= thresh:
        matched.append({"name": lq._text_prop(p, lq.PROP_PJNAME), "gross": gross, "req": req_sk})

sys.stdout.buffer.write(f"Final matched: {len(matched)}\n".encode("utf-8"))
for m in matched[:10]:
    sys.stdout.buffer.write(f"  {m['name'][:25]} gross={m['gross']:.0f} req={m['req']}\n".encode("utf-8"))
