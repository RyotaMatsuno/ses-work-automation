import io
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ── hex値確認（既に survey.pyで取得済み）──────────────────────────────
# 所属担当者名 = e68980e5b19ee68b85e5bd93e88085e5908d
# 所属メール   = e68980e5b19ee383a1e383bce383ab
print("hex確認:")
print(f"  所属担当者名: {bytes.fromhex('e68980e5b19ee68b85e5bd93e88085e5908d').decode()}")
print(f"  所属メール  : {bytes.fromhex('e68980e5b19ee383a1e383bce383ab').decode()}")
print()

paths = [
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py",
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py",
]

NEW_SRC = r'''import logging
import os
import re
from datetime import date, datetime, timedelta
from typing import Any

import jpholiday
import requests
from dateutil import parser
from dotenv import dotenv_values

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "config", ".env"))
CONFIG = dotenv_values(ENV_PATH)

NOTION_TOKEN = (
    CONFIG.get("NOTION_TOKEN")
    or CONFIG.get("NOTION_API_KEY")
    or os.environ.get("NOTION_TOKEN")
    or os.environ.get("NOTION_API_KEY")
    or ""
)
ENGINEER_DB_ID = (
    CONFIG.get("ENGINEER_DB_ID")
    or CONFIG.get("NOTION_ENGINEER_DB_ID")
    or os.environ.get("ENGINEER_DB_ID")
    or os.environ.get("NOTION_ENGINEER_DB_ID")
    or ""
)
PROJECT_DB_ID = (
    CONFIG.get("PROJECT_DB_ID")
    or CONFIG.get("NOTION_PROJECT_DB_ID")
    or os.environ.get("PROJECT_DB_ID")
    or os.environ.get("NOTION_PROJECT_DB_ID")
    or ""
)

NOTION_VERSION = "2022-06-28"
NOTION_QUERY_URL = "https://api.notion.com/v1/databases/{db_id}/query"
ERROR_MESSAGE = "\u7167\u4f1a\u4e2d\u306b\u30a8\u30e9\u30fc\u304c\u767a\u751f\u3057\u307e\u3057\u305f\u3002\u3057\u3070\u3089\u304f\u5f8c\u306b\u518d\u8a66\u884c\u3057\u3066\u304f\u3060\u3055\u3044\u3002"
LINE_LIMIT = 5000
TOP_LIMIT = 5
GROSS_THRESHOLDS = {"\u677e\u91ce": 5, "\u5ca1\u672c": 3, "\u5171\u901a": 3}

logger = logging.getLogger(__name__)

# ======================================================================
# Notion property constants  (UTF-8 bytes — no Japanese literals)
# ======================================================================
PROP_INI        = bytes.fromhex("e382a4e3838be382b7e383a3e383ab").decode()  # イニシャル
PROP_NAME       = bytes.fromhex("e5908de5898d").decode()                    # 名前
PROP_STA        = bytes.fromhex("e69c80e5af84e3828ae9a785").decode()        # 最寄り駅
PROP_MEMO       = bytes.fromhex("e58299e88083efbc884c494e45e383a1e383a2efbc89").decode()  # 備考（LINEメモ）
PROP_SKILL      = bytes.fromhex("e382b9e382ade383ab").decode()              # スキル
PROP_RATE       = bytes.fromhex("e58d98e4bea1efbc88e4b887e58686efbc89").decode()  # 単価（万円）
PROP_STATUS     = bytes.fromhex("e382b9e38386e383bce382bfe382b9").decode()  # ステータス
PROP_REQSK      = bytes.fromhex("e5bf85e8a681e382b9e382ade383ab").decode()  # 必要スキル
PROP_OPTSK      = bytes.fromhex("e5b09ae58fafe382b9e382ade383ab").decode()  # 尚可スキル   ← faf(可)
PROP_ASSIGNEE   = bytes.fromhex("e68b85e5bd93e88085").decode()              # 担当者
PROP_PJNAME     = bytes.fromhex("e6a188e4bbb6e5908d").decode()              # 案件名
PROP_PJDETAIL   = bytes.fromhex("e6a188e4bbb6e8a9b3e7b4b0").decode()       # 案件詳細
PROP_REMOTE     = bytes.fromhex("e383aae383a2e383bce38388").decode()        # リモート
PROP_LOCATION   = bytes.fromhex("e58ba4e58b99e59cb0").decode()              # 勤務地
PROP_PERIOD     = bytes.fromhex("e69c9fe99693").decode()                    # 期間
PROP_WORKON     = bytes.fromhex("e7a8bce5838de58fafe883bde697a5").decode()  # 稼働可能日
PROP_WORKST     = bytes.fromhex("e7a8bce5838de78ab6e6b381").decode()        # 稼働状況
PROP_AFFIL      = bytes.fromhex("e68980e5b19ee4bc9ae7a4be").decode()        # 所属会社
PROP_AFFIL_CONT = bytes.fromhex("e68980e5b19ee68b85e5bd93e88085e5908d").decode()  # 所属担当者名
PROP_AFFIL_MAIL = bytes.fromhex("e68980e5b19ee383a1e383bce383ab").decode()  # 所属メール
VAL_RECRUITING  = bytes.fromhex("e58b9fe99b86e4b8ad").decode()              # 募集中
VAL_ACTIVE2     = bytes.fromhex("e7a8bce5838de58fafe883bd").decode()        # 稼働可能
VAL_ADJUSTING   = bytes.fromhex("e8aabfe695b4e4b8ad").decode()              # 調整中
# ======================================================================


def _notion_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json; charset=utf-8",
        "Notion-Version": NOTION_VERSION,
    }


def fetch_all_pages(db_id: str, filter_body: dict = None) -> list[dict]:
    results: list[dict] = []
    payload: dict[str, Any] = {"page_size": 100}
    if filter_body:
        payload["filter"] = filter_body
    while True:
        response = requests.post(
            NOTION_QUERY_URL.format(db_id=db_id),
            headers=_notion_headers(),
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        results.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data.get("next_cursor")
    return results


def business_days_since(dt) -> int:
    if isinstance(dt, str):
        start_date = parser.isoparse(dt).date()
    elif isinstance(dt, datetime):
        start_date = dt.date()
    elif isinstance(dt, date):
        start_date = dt
    else:
        raise TypeError("dt must be datetime, date, or ISO string")
    today = date.today()
    if start_date >= today:
        return 0
    days = 0
    current = start_date + timedelta(days=1)
    while current <= today:
        if current.weekday() < 5 and not jpholiday.is_holiday(current):
            days += 1
        current += timedelta(days=1)
    return days


def classify_query(text: str) -> tuple[str, dict]:
    stripped = text.strip()
    _m = re.match(r"^([A-Za-z.]{1,8})[\s\u3000/]+(.+)$", stripped)
    if _m:
        _raw = _m.group(1).strip(".")
        _sta = _m.group(2).strip()
        if re.match(r"^[A-Za-z.]+$", _raw) and len(_raw) >= 1:
            _ini = re.sub(r"[.]", "", _raw).upper()
            return ("engineer", {"initial": _ini, "station": _sta})
    return ("project", {"name": stripped})


def skill_match(required: list[str], engineer_skills: list[str]) -> bool:
    if not required:
        return True
    engineer_lower = [s.lower() for s in engineer_skills if s]
    for req in required:
        if not any(req.lower() in s for s in engineer_lower):
            return False
    return True


def calc_gross_profit(budget: float, cost: float) -> float:
    return float(budget or 0) - float(cost or 0)


def _normalize_initial(s: str) -> str:
    return re.sub(r"[\s\u3000.\u30fb\u00b7]", "", s).upper()


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


def _clean_detail(text: str, max_len: int = 200) -> str:
    """案件詳細から自動登録ヘッダーを除去して業務内容を抽出する"""
    if not text:
        return ""
    # 自動登録ヘッダーを除去（送信者/件名行をスキップ）
    skip_markers = (
        "\u30e1\u30fc\u30eb\u304b\u3089\u81ea\u52d5\u767b\u9332",  # メールから自動登録
        "[LINE auto-register",
        "\u9001\u4fe1\u8005:",   # 送信者:
        "\u4ef6\u540d:",         # 件名:
    )
    lines = text.split("\n")
    start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not any(m in stripped for m in skip_markers):
            # 挨拶文・本文前置きもスキップ
            greet = ("\u3054\u62c5\u5f53\u8005\u69d8",  # ご担当者様
                     "\u304a\u4e16\u8a71\u306b\u306a\u3063\u3066",  # お世話になって
                     "\u8a72\u5f53\u4eba\u6750\u304c\u3044\u3089\u3063\u3057\u3083",  # 該当人材がいらっしゃ
                     "\u30a8\u30f3\u30c8\u30ea\u30fc\u3044\u305f\u3060\u3051\u308b",  # エントリーいただける
                     "BCCにて", "BCC\u306b\u3066")
            if any(g in stripped for g in greet):
                continue
            start = i
            break
    text = "\n".join(lines[start:]).strip()

    # 業務内容マーカーがあればその後ろから取得
    markers = (
        "\u300a\u696d\u52d9\u5185\u5bb9\u300b",  # 《業務内容》
        "\u3010\u696d\u52d9\u5185\u5bb9\u3011",  # 【業務内容】
        "\u3010\u4f5c\u696d\u5185\u5bb9\u3011",  # 【作業内容】
        "\u3010\u696d\u52d9\u6982\u8981\u3011",  # 【業務概要】
        "\u3010\u696d\u52d9\u8a73\u7d30\u3011",  # 【業務詳細】
        "\u696d\u52d9\u5185\u5bb9\uff1a",        # 業務内容：
        "\u4f5c\u696d\u5185\u5bb9\uff1a",        # 作業内容：
        "\uff1c\u696d\u52d9\u5185\u5bb9\uff1e",  # ＜業務内容＞
    )
    for m in markers:
        idx = text.find(m)
        if idx >= 0:
            text = text[idx + len(m):].strip()
            break

    # 改行を整理して truncate
    text = re.sub(r"\n+", " ", text).strip()
    if len(text) > max_len:
        return text[:max_len] + "..."
    return text


def engineer_query(initial: str, station: str) -> str:
    engineers = fetch_all_pages(ENGINEER_DB_ID)
    matched_engineers = [
        e for e in engineers
        if _match_initial(e, initial) and _match_station(e, station)
    ]
    if not matched_engineers:
        return f"\u4e00\u81f4\u3059\u308b\u4eba\u54e1\u304c\u898b\u3064\u304b\u308a\u307e\u305b\u3093\u3067\u3057\u305f: {initial} {station}"

    _prj_filter = {
        "and": [
            {"property": PROP_STATUS, "select": {"equals": VAL_RECRUITING}},
            {"property": PROP_RATE,   "number": {"greater_than": 0}},
        ]
    }
    projects = fetch_all_pages(PROJECT_DB_ID, filter_body=_prj_filter)

    # dedup: 先頭20文字で重複排除（同一案件の複数メール送信に対応）
    _seen: set[str] = set()
    _deduped: list[dict] = []
    for _p in projects:
        _k = _text_prop(_p, PROP_PJNAME)
        _k20 = _k[:20] if _k else ""
        if _k20 and _k20 not in _seen:
            _seen.add(_k20)
            _deduped.append(_p)
    projects = _deduped

    replies = []
    for engineer in matched_engineers:
        eng_skills = _multi_select_prop(engineer, PROP_SKILL)
        eng_rate   = _number_prop(engineer, PROP_RATE)
        matched: list[dict] = []
        for project in projects:
            if business_days_since(project.get("last_edited_time")) > 4:
                continue
            required = _multi_select_prop(project, PROP_REQSK)
            if not required:
                continue  # スキル未設定案件はマッチング対象外
            if not skill_match(required, eng_skills):
                continue
            budget = _number_prop(project, PROP_RATE)
            if budget > 150:
                continue  # 異常単価除外
            gross  = calc_gross_profit(budget, eng_rate)
            thresh = _gross_threshold(_select_prop(project, PROP_ASSIGNEE))
            if gross < thresh:
                continue
            matched.append({"page": project, "gross_profit": gross})
        matched.sort(key=lambda x: x["gross_profit"], reverse=True)
        replies.append(format_project_result(engineer, matched))
    return "\n\n".join(replies)


def project_query(name: str) -> str:
    _filter = {"property": PROP_STATUS, "select": {"equals": VAL_RECRUITING}}
    projects = fetch_all_pages(PROJECT_DB_ID, filter_body=_filter)
    matched = [p for p in projects if _contains(_text_prop(p, PROP_PJNAME), name)]
    if not matched:
        return f"\u4e00\u81f4\u3059\u308b\u6848\u4ef6\u304c\u898b\u3064\u304b\u308a\u307e\u305b\u3093\u3067\u3057\u305f: {name}"
    project = matched[0]
    required  = _multi_select_prop(project, PROP_REQSK)
    budget    = _number_prop(project, PROP_RATE)
    threshold = _gross_threshold(_select_prop(project, PROP_ASSIGNEE))
    engineers = fetch_all_pages(ENGINEER_DB_ID)
    matched_engs = []
    for eng in engineers:
        if _select_prop(eng, PROP_WORKST) not in (VAL_ACTIVE2, VAL_ADJUSTING):
            continue
        if business_days_since(eng.get("last_edited_time")) > 21:
            continue
        if not skill_match(required, _multi_select_prop(eng, PROP_SKILL)):
            continue
        gross = calc_gross_profit(budget, _number_prop(eng, PROP_RATE))
        if gross < threshold:
            continue
        matched_engs.append({"page": eng, "gross_profit": gross})
    matched_engs.sort(key=lambda x: x["gross_profit"], reverse=True)
    return format_engineer_result(project, matched_engs)


def format_project_result(engineer: dict, projects: list) -> str:
    initial = _text_prop(engineer, PROP_INI) or _normalize_initial(_text_prop(engineer, PROP_NAME))
    station = _text_prop(engineer, PROP_STA)

    # 所属連絡先（意向確認用）
    affil      = _text_prop(engineer, PROP_AFFIL)
    affil_cont = _text_prop(engineer, PROP_AFFIL_CONT)
    affil_mail = _text_prop(engineer, PROP_AFFIL_MAIL)

    if not projects:
        return (
            f"\u3010{initial}\uff5c{station}\u3011\u30de\u30c3\u30c1\u6848\u4ef6\u306a\u3057\n"
            "\uff08\u6761\u4ef6: \u6709\u52b9\u6848\u4ef6\u306a\u3057 or \u30b9\u30ad\u30eb\u30fb\u7c97\u5229\u4e0d\u4e00\u81f4\uff09"
        )

    lines = [f"\u3010{initial}\uff5c{station}\u3011\u30de\u30c3\u30c1\u6848\u4ef6 {len(projects)}\u4ef6"]

    # 所属情報ライン（意向確認先）
    affil_parts = [p for p in [affil, affil_cont, affil_mail] if p]
    if affil_parts:
        lines.append("\u6240\u5c5e: " + " / ".join(affil_parts))  # 所属:

    for idx, item in enumerate(projects, 1):
        pj       = item["page"]
        pj_name  = _text_prop(pj, PROP_PJNAME)
        req_sk   = _join(_multi_select_prop(pj, PROP_REQSK))
        opt_sk   = _join(_multi_select_prop(pj, PROP_OPTSK))
        loc      = _text_prop(pj, PROP_LOCATION)
        remote   = _select_prop(pj, PROP_REMOTE)
        period   = _text_prop(pj, PROP_PERIOD)
        budget   = _number_prop(pj, PROP_RATE)
        gross    = item["gross_profit"]
        age      = business_days_since(pj.get("last_edited_time"))
        assignee = _select_prop(pj, PROP_ASSIGNEE)
        detail   = _clean_detail(_text_prop(pj, PROP_PJDETAIL))

        lines.extend([
            "",
            f"{_num_label(idx)} {pj_name}",
            f"  \u5fc5\u9808: {req_sk}" + (f" / \u5c1a\u53ef: {opt_sk}" if opt_sk else ""),
            f"  \u5358\u4fa1: {_format_number(budget)}\u4e07 / \u7c97\u5229: {_format_number(gross)}\u4e07 / {assignee}\u62c5\u5f53",
            f"  {loc}({remote})" + (f" / {period}" if period else "") + f" [{age}\u65e5\u524d]",
        ])
        if detail:
            lines.append(f"  \u6982\u8981: {detail}")  # 概要:

    return _limit_reply(lines, projects, format_project_result, engineer)


def format_engineer_result(project: dict, engineers: list) -> str:
    pj_name = _text_prop(project, PROP_PJNAME)
    if not engineers:
        return (
            f"\u3010{pj_name}\u3011\u30de\u30c3\u30c1\u4eba\u54e1\u306a\u3057\n"
            "\uff08\u6761\u4ef6: \u30b9\u30ad\u30eb\u30fb\u7c97\u5229\u30fb\u9256\u5ea6\u6761\u4ef6\u4e0d\u4e00\u81f4\uff09"
        )
    lines = [f"\u3010{pj_name}\u3011\u30de\u30c3\u30c1\u4eba\u54e1 {len(engineers)}\u540d"]
    for idx, item in enumerate(engineers, 1):
        eng = item["page"]
        lines.extend([
            "",
            f"{_num_label(idx)}{_text_prop(eng, PROP_NAME)}\uff5c{_text_prop(eng, PROP_STA)}",
            f"  \u30b9\u30ad\u30eb: {_join(_multi_select_prop(eng, PROP_SKILL))}",
            f"  \u7a3c\u50cd: {_select_prop(eng, PROP_WORKST)} / \u5358\u4fa1: {_format_number(_number_prop(eng, PROP_RATE))}\u4e07 / \u7c97\u5229: {_format_number(item['gross_profit'])}\u4e07",
            f"  \u7a3c\u50cd\u53ef: {_date_prop(eng, PROP_WORKON) or '\u672a\u8a2d\u5b9a'} / \u9256\u5ea6: {business_days_since(eng.get('last_edited_time'))}\u65e5\u524d",
            f"  \u6240\u5c5e: {_text_prop(eng, PROP_AFFIL)} / {_text_prop(eng, PROP_AFFIL_CONT)} / {_text_prop(eng, PROP_AFFIL_MAIL)}",
        ])
    return _limit_reply(lines, engineers, format_engineer_result, project)


def handle_line_query(text: str) -> str | None:
    if not text or not text.strip():
        return None
    if len(text.strip()) > 100:
        return None
    try:
        query_type, params = classify_query(text)
        if query_type == "engineer":
            result = engineer_query(params["initial"], params["station"])
        else:
            result = project_query(params["name"])
        no_match_phrases = (
            "\u4e00\u81f4\u3059\u308b\u4eba\u54e1\u304c\u898b\u3064\u304b\u308a\u307e\u305b\u3093",
            "\u4e00\u81f4\u3059\u308b\u6848\u4ef6\u304c\u898b\u3064\u304b\u308a\u307e\u305b\u3093",
        )
        if result and any(p in result for p in no_match_phrases):
            return None
        return result if result else None
    except Exception:
        logger.exception("line_query failed")
        return None


# ── Notion helpers ──────────────────────────────────────────────────

def _prop(page: dict, name: str) -> dict:
    return page.get("properties", {}).get(name, {})

def _text_prop(page: dict, name: str) -> str:
    prop = _prop(page, name)
    ptype = prop.get("type")
    if ptype == "title":
        values = prop.get("title", [])
    elif ptype == "rich_text":
        values = prop.get("rich_text", [])
    elif ptype == "email":
        return prop.get("email") or ""
    else:
        return ""
    return "".join(item.get("plain_text", "") for item in values).strip()

def _multi_select_prop(page: dict, name: str) -> list[str]:
    return [x.get("name", "") for x in _prop(page, name).get("multi_select", []) if x.get("name")]

def _select_prop(page: dict, name: str) -> str:
    v = _prop(page, name).get("select")
    return v.get("name", "") if v else ""

def _number_prop(page: dict, name: str) -> float:
    v = _prop(page, name).get("number")
    return float(v or 0)

def _date_prop(page: dict, name: str) -> str:
    v = _prop(page, name).get("date")
    return v.get("start", "") if v else ""

def _contains(value: str, keyword: str) -> bool:
    return keyword.lower() in value.lower()

def _gross_threshold(assignee: str) -> int:
    return GROSS_THRESHOLDS.get(assignee, 3)

def _join(values: list[str]) -> str:
    return " / ".join(values)

def _format_number(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return f"{value:.1f}".rstrip("0").rstrip(".")

def _num_label(index: int) -> str:
    labels = "\u2460\u2461\u2462\u2463\u2464\u2465\u2466\u2467\u2468\u2469"
    return labels[index - 1] if 1 <= index <= len(labels) else f"{index}."

def _limit_reply(lines: list[str], items: list, formatter, header_page: dict) -> str:
    text = "\n".join(lines)
    if len(text) <= LINE_LIMIT:
        return text
    limited = lines[:2]  # ヘッダー2行（タイトル＋所属行）を保持
    for line in lines[2:]:
        if line.startswith(_num_label(TOP_LIMIT + 1)):
            break
        limited.append(line)
    out = "\n".join(limited)
    suffix = "\n(\u4e0a\u4f4d5\u4ef6\u8868\u793a)"
    if len(out) + len(suffix) > LINE_LIMIT:
        out = out[: LINE_LIMIT - len(suffix)]
    return out + suffix


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, encoding="utf-8")
    for case in ["HS \u5317\u5c0f\u91d1", "H.S \u5317\u5c0f\u91d1", "TK \u6e0b\u8c37"]:
        print(f"\n--- {case} ---")
        print(handle_line_query(case))
'''

for path in paths:
    with open(path, "w", encoding="utf-8") as f:
        f.write(NEW_SRC)
    r = subprocess.run(["python", "-m", "py_compile", path], capture_output=True, text=True)
    fname = "/".join(path.split("\\")[-2:])
    print(f"{'✅' if r.returncode == 0 else '❌'} {fname}: 構文{'OK' if r.returncode == 0 else r.stderr}")
