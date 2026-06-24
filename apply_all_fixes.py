"""
line_query.py 完全修正スクリプト
- バックアップから復元済みのクリーンファイルに対して
- 全プロパティキーをbytes定数化
- engineer_query を完全書き直し（Notionフィルタ付き）
- _match_initial / _match_station の修正
- 構文チェック通過を確認
"""

import subprocess
import sys

SRC = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"

with open(SRC, "rb") as f:
    raw = f.read()

text = raw.decode("utf-8", errors="replace")

# ======== Step1: プロパティ定数ブロックを logger 行直後に挿入 ========
CONST_BLOCK = b"""
# === Notion property/value constants (ASCII-safe, no Japanese literals) ===
PROP_INI      = bytes.fromhex('e382a4e3838be382b7e383a3e383ab').decode('utf-8')  # noqa
PROP_NAME     = bytes.fromhex('e5908de5898d').decode('utf-8')                    # noqa
PROP_STA      = bytes.fromhex('e69c80e5af84e3828ae9a785').decode('utf-8')        # noqa
PROP_MEMO     = bytes.fromhex('e58299e88083efbc884c494e45e383a1e383a2efbc89').decode('utf-8')  # noqa
PROP_SKILL    = bytes.fromhex('e382b9e382ade383ab').decode('utf-8')              # noqa
PROP_RATE     = bytes.fromhex('e58d98e4bea1efbc88e4b887e58686efbc89').decode('utf-8')  # noqa
PROP_STATUS   = bytes.fromhex('e382b9e38386e383bce382bfe382b9').decode('utf-8')  # noqa
PROP_REQSK    = bytes.fromhex('e5bf85e8a681e382b9e382ade383ab').decode('utf-8')  # noqa
PROP_OPTSK    = bytes.fromhex('e5b09ae58fafe382b9e382ade383ab').decode('utf-8')  # noqa
PROP_ASSIGNEE = bytes.fromhex('e68b85e5bd93e88085').decode('utf-8')             # noqa
PROP_PJNAME   = bytes.fromhex('e6a188e4bbb6e5908d').decode('utf-8')             # noqa
PROP_PJDETAIL = bytes.fromhex('e6a188e4bbb6e8a9b3e7b4b0').decode('utf-8')      # noqa
PROP_REMOTE   = bytes.fromhex('e383aae383a2e383bce38388').decode('utf-8')       # noqa
PROP_LOCATION = bytes.fromhex('e58ba4e58b99e59cb0').decode('utf-8')             # noqa
PROP_PERIOD   = bytes.fromhex('e69c9fe99693').decode('utf-8')                   # noqa
PROP_INTERVIEW= bytes.fromhex('e99da2e8ab87e5b88ce69c9b').decode('utf-8')      # noqa
PROP_WORKON   = bytes.fromhex('e7a8bce5838de58fafe883bde697a5').decode('utf-8') # noqa
PROP_WORKST   = bytes.fromhex('e7a8bce5838de78ab6e6b381').decode('utf-8')      # noqa
PROP_AFFIL    = bytes.fromhex('e68980e5b19ee4bc9ae7a4be').decode('utf-8')      # noqa
VAL_RECRUITING= bytes.fromhex('e58b9fe99b86e4b8ad').decode('utf-8')            # noqa
# ==========================================================================
"""

marker = b"logger = logging.getLogger(__name__)"
idx = raw.find(marker)
line_end = raw.find(b"\n", idx) + 1
raw = raw[:line_end] + CONST_BLOCK + raw[line_end:]
sys.stdout.buffer.write(b"Step1: constants inserted\n")

# ======== Step2: engineer_query を完全書き換え ========
text = raw.decode("utf-8", errors="replace")
eq_start = text.find("def engineer_query(")
eq_end = text.find("\ndef project_query(")
if eq_start == -1 or eq_end == -1:
    sys.stdout.buffer.write(f"ERROR markers: eq_start={eq_start} eq_end={eq_end}\n".encode())
    sys.exit(1)

NEW_EQ = b'''def engineer_query(initial: str, station: str) -> str:
    """Return matching projects for engineer identified by initial+station."""
    engineers = fetch_all_pages(ENGINEER_DB_ID)
    matched_engineers = [
        e for e in engineers
        if _match_initial(e, initial) and _match_station(e, station)
    ]
    if not matched_engineers:
        no_match = bytes.fromhex('e4b880e887b4e38199e3828be4babae593a1e3818ce898b8e381a4e3818be3828ae381bee3819be38293e381a7e38197e3819f').decode('utf-8')
        return no_match + ': ' + initial + ' ' + station

    # Notion-side filter: budget>=75 AND status=recruiting (reduces API load)
    _prj_filter = {
        'and': [
            {'property': PROP_RATE,   'number': {'greater_than_or_equal_to': 75}},
            {'property': PROP_STATUS, 'select': {'equals': VAL_RECRUITING}},
        ]
    }
    projects = fetch_all_pages(PROJECT_DB_ID, filter_body=_prj_filter)

    replies = []
    for engineer in matched_engineers:
        engineer_skills = _multi_select_prop(engineer, PROP_SKILL)
        engineer_rate   = _number_prop(engineer, PROP_RATE)
        matched_projects = []
        for project in projects:
            if business_days_since(project.get('last_edited_time')) > 4:
                continue
            required = _multi_select_prop(project, PROP_REQSK)
            if not skill_match(required, engineer_skills):
                continue
            budget = _number_prop(project, PROP_RATE)
            gross  = calc_gross_profit(budget, engineer_rate)
            if gross < _gross_threshold(_select_prop(project, PROP_ASSIGNEE)):
                continue
            matched_projects.append({'page': project, 'gross_profit': gross})
        matched_projects.sort(key=lambda item: item['gross_profit'], reverse=True)
        replies.append(format_project_result(engineer, matched_projects))
    return '\\n\\n'.join(replies)

'''

before = text[:eq_start].encode("utf-8")
after = text[eq_end:].encode("utf-8")
raw = before + NEW_EQ + after
sys.stdout.buffer.write(b"Step2: engineer_query rewritten\n")

# ======== Step3: _normalize_initial / _match_initial / _match_station 修正 ========
text = raw.decode("utf-8", errors="replace")

NEW_MATCH = b"""def _normalize_initial(s: str) -> str:
    import re as _re2
    return _re2.sub(r'[\\s\\u3000.\\u30fb\\u00b7]', '', s).upper()


def _match_initial(engineer: dict, initial: str) -> bool:
    ini = _text_prop(engineer, PROP_INI)
    if ini:
        return _normalize_initial(ini) == initial.upper()
    name = _text_prop(engineer, PROP_NAME)
    return _normalize_initial(name) == initial.upper()


def _match_station(engineer: dict, station: str) -> bool:
    if not station:
        return True
    sta = _text_prop(engineer, PROP_STA)
    if sta:
        return station in sta
    memo = _text_prop(engineer, PROP_MEMO)
    if memo and station in memo:
        return True
    return True  # no station data -> match by initial only


"""

s3_start = text.find("def _normalize_initial(")
s3_end = text.find("def engineer_query(")
if s3_start == -1 or s3_end == -1:
    sys.stdout.buffer.write(f"Step3 markers not found: {s3_start} {s3_end}\n".encode())
else:
    before3 = text[:s3_start].encode("utf-8")
    after3 = text[s3_end:].encode("utf-8")
    raw = before3 + NEW_MATCH + after3
    sys.stdout.buffer.write(b"Step3: _match functions rewritten\n")

# ======== Step4: fetch_all_pages に filter_body 引数追加 ========
text = raw.decode("utf-8", errors="replace")
old_sig = "def fetch_all_pages(db_id: str) -> list[dict]:"
new_sig = "def fetch_all_pages(db_id: str, filter_body: dict = None) -> list[dict]:"
if old_sig in text:
    text = text.replace(old_sig, new_sig, 1)
    sys.stdout.buffer.write(b"Step4a: fetch_all_pages sig updated\n")

old_payload = '    payload: dict[str, Any] = {"page_size": 100}\n'
new_payload = (
    '    payload: dict[str, Any] = {"page_size": 100}\n    if filter_body:\n        payload["filter"] = filter_body\n'
)
if old_payload in text:
    text = text.replace(old_payload, new_payload, 1)
    sys.stdout.buffer.write(b"Step4b: payload filter added\n")

raw = text.encode("utf-8")

# ======== 書き込み & 構文チェック ========
with open(SRC, "wb") as f:
    f.write(raw)

result = subprocess.run(
    ["python", "-m", "py_compile", SRC], capture_output=True, text=True, encoding="utf-8", errors="replace"
)
if result.returncode == 0:
    sys.stdout.buffer.write(b"Syntax: OK\n")
else:
    sys.stdout.buffer.write(f"Syntax ERROR: {result.stderr}\n".encode())
