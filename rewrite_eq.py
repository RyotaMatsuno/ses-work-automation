import sys

fpath = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(fpath, "rb") as f:
    raw = f.read()
text = raw.decode("utf-8", errors="replace")

# engineer_query から project_query の直前までを完全置換
start_marker = "def engineer_query("
end_marker = "def project_query("

start = text.find(start_marker)
end = text.find(end_marker)

if start == -1 or end == -1:
    sys.stdout.buffer.write(f"MARKERS NOT FOUND: start={start} end={end}\n".encode())
    sys.exit(1)

sys.stdout.buffer.write(f"Replacing bytes {start}-{end}\n".encode())

# 新しい engineer_query をbytesで構築（日本語なし、定数参照のみ）
new_func = b"""def engineer_query(initial: str, station: str) -> str:
    engineers = fetch_all_pages(ENGINEER_DB_ID)
    matched_engineers = [
        e for e in engineers
        if _match_initial(e, initial) and _match_station(e, station)
    ]
    if not matched_engineers:
        return "\\u4e00\\u81f4\\u3059\\u308b\\u4eba\\u54e1\\u304c\\u898b\\u3064\\u304b\\u308a\\u307e\\u305b\\u3093\\u3067\\u3057\\u305f: " + initial + " " + station
    from datetime import datetime, timezone, timedelta
    import jpholiday as _jph
    def _biz_days(ts):
        if not ts:
            return 999
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        today = datetime.now(timezone.utc).date()
        d = dt.date()
        count = 0
        cur = d
        while cur < today:
            cur += timedelta(days=1)
            if cur.weekday() < 5 and not _jph.is_holiday(cur):
                count += 1
        return count
    # Notion-side pre-filter: budget>=75 AND status=recruiting
    _prj_filter = {"and": [
        {"property": PROP_RATE, "number": {"greater_than_or_equal_to": 75}},
        {"property": PROP_STATUS, "select": {"equals": VAL_RECRUITING}}
    ]}
    projects = fetch_all_pages(PROJECT_DB_ID, filter_body=_prj_filter)
    replies = []
    for engineer in matched_engineers:
        engineer_skills = _multi_select_prop(engineer, PROP_SKILL)
        engineer_rate   = _number_prop(engineer, PROP_RATE)
        matched_projects = []
        for project in projects:
            if _biz_days(project.get("last_edited_time")) > 4:
                continue
            required = _multi_select_prop(project, PROP_REQSK)
            if not skill_match(required, engineer_skills):
                continue
            budget = _number_prop(project, PROP_RATE)
            gross  = calc_gross_profit(budget, engineer_rate)
            if gross < _gross_threshold(_select_prop(project, PROP_ASSIGNEE)):
                continue
            matched_projects.append({"page": project, "gross_profit": gross})
        matched_projects.sort(key=lambda item: item["gross_profit"], reverse=True)
        replies.append(format_project_result(engineer, matched_projects))
    return "\\n\\n".join(replies)


"""

# before + new_func + from end_marker
before_bytes = text[:start].encode("utf-8")
after_bytes = text[end:].encode("utf-8")
new_raw = before_bytes + new_func + after_bytes

with open(fpath, "wb") as f:
    f.write(new_raw)

# 構文チェック
import subprocess

result = subprocess.run(
    ["python", "-m", "py_compile", fpath], capture_output=True, text=True, encoding="utf-8", errors="replace"
)
if result.returncode == 0:
    sys.stdout.buffer.write(b"Syntax OK\n")
else:
    sys.stdout.buffer.write(f"Syntax ERROR: {result.stderr}\n".encode())
