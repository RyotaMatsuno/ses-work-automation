"""
LINE Webhook Server v10
- 莠ｺ蜩｡逋ｻ骭ｲ譎ゅ↓譌｢蟄伜供髮・ｸｭ譯井ｻｶ縺ｨ騾・・繝・メ繝ｳ繧ｰ
- 縲碁∽ｿ｡縺励※ [繝｡繧｢繝云縲阪〒ses-mail邨檎罰縺ｮ螳溘Γ繝ｼ繝ｫ騾∽ｿ｡
- NG蛟呵｣懊ｒ笳凝嶺ｻ倥″縺ｧ蜿り・｡ｨ遉ｺ縲≫無繧ょ性繧√※騾∽ｿ｡縺ｫ蟇ｾ蠢・
"""

import os, hmac, hashlib, base64, json, re, traceback
from datetime import date
from flask import Flask, request, abort
import requests
from dotenv import dotenv_values, set_key

ENV_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', '.env')
if os.path.exists(ENV_PATH):
    config = dotenv_values(ENV_PATH)
    for key, value in config.items():
        if key not in os.environ:
            os.environ[key] = value

MATSUNO_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET', '')
MATSUNO_CHANNEL_TOKEN  = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', '')
MATSUNO_USER_ID        = os.environ.get('MATSUNO_LINE_USER_ID', '')
OKAMOTO_CHANNEL_SECRET = os.environ.get('OKAMOTO_LINE_CHANNEL_SECRET', '')
OKAMOTO_CHANNEL_TOKEN  = os.environ.get('OKAMOTO_LINE_CHANNEL_ACCESS_TOKEN', '')
OKAMOTO_USER_ID        = os.environ.get('OKAMOTO_LINE_USER_ID', '')
NOTION_API_KEY         = os.environ.get('NOTION_API_KEY', '')
NOTION_ENGINEER_DB_ID  = os.environ.get('NOTION_ENGINEER_DB_ID', '')
NOTION_PROJECT_DB_ID   = os.environ.get('NOTION_PROJECT_DB_ID', '')
ANTHROPIC_API_KEY      = os.environ.get('ANTHROPIC_API_KEY', '')

# ses-mail API繧ｨ繝ｳ繝峨・繧､繝ｳ繝茨ｼ・laude Desktop MCP邨檎罰縺ｧ縺ｯ縺ｪ縺上Ο繝ｼ繧ｫ繝ｫ繧ｵ繝ｼ繝舌・逶ｴ謗･蜻ｼ縺ｳ蜃ｺ縺暦ｼ・
# Railway荳翫〒縺ｯses-mail縺ｯ菴ｿ縺医↑縺・◆繧√・∽ｿ｡謖・､ｺ縺ｯ繝ｭ繝ｼ繧ｫ繝ｫ縺ｸ縺ｮ繧ｳ繝ｼ繝ｫ繝舌ャ繧ｯ譁ｹ蠑上〒蛻･騾泌ｯｾ蠢・
# 竊・迴ｾ迥ｶ縺ｯ縲碁∽ｿ｡蜀・ｮｹ繧鱈INE縺ｫ霑斐☆縲搾ｼ九梧收驥弱′ses-mail縺ｧ謇句虚騾∽ｿ｡縲阪ヵ繝ｭ繝ｼ
# TODO: Railway竊偵Ο繝ｼ繧ｫ繝ｫ繧ｵ繝ｼ繝舌・縺ｸ縺ｮ繧ｳ繝ｼ繝ｫ繝舌ャ繧ｯ螳溯｣・ｾ後↓閾ｪ蜍募喧

app = Flask(__name__)
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}
VALID_SKILLS = [
    "Java","Python","PHP","JavaScript","TypeScript","C#","Node.js","React","AWS",
    "Go","Ruby","Swift","Kotlin","Vue.js","Angular","Docker","Kubernetes","GCP",
    "Azure","Spring","MySQL","PostgreSQL","Oracle","MongoDB","Linux","Salesforce",
    "SAP","Tableau","PowerBI","Terraform","Jenkins","GitLab"
]

SHEET_URL_PATTERN = re.compile(r'https://docs\.google\.com/spreadsheets/[^\s]+')
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')

# 騾∽ｿ｡蠕・■謠先｡医ｒ荳譎ゆｿ晏ｭ・
# key: sender+"_latest" 竊・{"ok": [...], "ng": [...], "proposal_draft": "", "proj_name": ""}
PENDING_PROPOSALS = {}


def verify_signature(body, signature, secret):
    h = hmac.new(secret.encode('utf-8'), body, hashlib.sha256).digest()
    return hmac.compare_digest(base64.b64encode(h).decode('utf-8'), signature)


def call_claude(system, user_msg, max_tokens=2000):
    res = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": "claude-haiku-4-5-20251001", "max_tokens": max_tokens,
              "system": system, "messages": [{"role": "user", "content": user_msg}]},
        timeout=60
    )
    if res.status_code == 200:
        return res.json()["content"][0]["text"]
    print(f"Claude API error: {res.status_code} {res.text[:100]}")
    return ""


def normalize_price(price):
    if price is None or price == 0:
        return price
    if price >= 1000:
        price = round(price / 10000)
    return price


def classify_message(text):
    system = '''SES business message classifier. Reply JSON only.
IMPORTANT: Ignore forwarding remarks (e.g. "縺薙ｌ縺ｩ縺・〒縺吶°", "蜴溘＆繧薙←縺・〒縺吶°") and extract only actual job/engineer info.
IMPORTANT: price field must be in 荳・・ unit as integer. e.g. "65荳・->65, "45荳・ｽ・0荳・->47 (midpoint), "650,000蜀・->65.

If the message contains ONE engineer:
{"type":"engineer","name":"","skills":[],"price":0,"available_date":"","experience_years":0,"note":""}

If the message contains MULTIPLE engineers:
{"type":"engineers","engineers":[{"name":"","skills":[],"price":0,"available_date":"","experience_years":0,"note":""},...]}

If the message contains ONE job posting:
{"type":"project","name":"","required_skills":[],"optional_skills":[],"price":0,"start_date":"","location":"","remote":"unknown","period":"","note":""}

If the message contains MULTIPLE job postings:
{"type":"projects","projects":[{"name":"","required_skills":[],"optional_skills":[],"price":0,"start_date":"","location":"","remote":"unknown","period":"","note":""},...]}

Otherwise:
{"type":"other","note":""}'''

    result = call_claude(system, text, max_tokens=2000)
    try:
        result_obj = json.loads(re.sub(r'```json|```', '', result).strip())
        if not isinstance(result_obj, dict):
            return {"type": "other", "note": text[:300]}
        return result_obj
    except Exception as e:
        print(f"[classify_message] parse error: {e} / raw: {result[:100]}")
        return {"type": "other", "note": text[:300]}


def classify_sheet_content(text):
    system = '''Classify this spreadsheet content. Reply JSON only.
{"content_type": "engineer"} or {"content_type": "project"}'''
    result = call_claude(system, text[:2000], max_tokens=100)
    try:
        return json.loads(re.sub(r'```json|```', '', result).strip()).get("content_type", "engineer")
    except Exception:
        return "engineer"


def fetch_sheet_text(url):
    try:
        import sys
        sys.path.insert(0, r'C:\Users\ma_py\OneDrive\繝・せ繧ｯ繝医ャ繝予ses_work\mail_attachment_importer')
        from sheet_fetcher import fetch_sheet_text as _fetch
        return _fetch(url)
    except Exception as e:
        return {"status": "error", "error": str(e)}


def extract_engineers_from_text(text):
    try:
        import sys
        sys.path.insert(0, r'C:\Users\ma_py\OneDrive\繝・せ繧ｯ繝医ャ繝予ses_work\mail_attachment_importer')
        from ai_extractor import extract_engineers
        return extract_engineers(text, "sheet_from_line")
    except Exception as e:
        return []


def extract_projects_from_text(text):
    try:
        import sys
        sys.path.insert(0, r'C:\Users\ma_py\OneDrive\繝・せ繧ｯ繝医ャ繝予ses_work\mail_attachment_importer')
        from ai_extractor import extract_projects
        return extract_projects(text, "sheet_from_line")
    except Exception as e:
        return []


def run_matching(project, engineers):
    """譯井ｻｶ 竊・莠ｺ蜩｡繝槭ャ繝√Φ繧ｰ"""
    system = '''SES matching AI. Reply JSON only.
Return ALL engineers as candidates with skill match evaluation.
{"candidates":[{
  "name":"",
  "price":0,
  "summary":"",
  "required_match":{"Java":true,"Python":false},
  "optional_match":{"Docker":true},
  "parallel":"none",
  "engineer_source":"matsuno or okamoto or unknown"
}],"proposal_draft":""}'''
    result = call_claude(system, json.dumps({"project": project, "engineers": engineers}, ensure_ascii=False), max_tokens=2000)
    try:
        result_obj = json.loads(re.sub(r'```json|```', '', result).strip())
        if not isinstance(result_obj, dict):
            return {"candidates": [], "proposal_draft": ""}
        return result_obj
    except Exception as e:
        print(f"[run_matching] parse error: {e}")
        return {"candidates": [], "proposal_draft": ""}


def run_reverse_matching(engineer, projects):
    """莠ｺ蜩｡ 竊・譯井ｻｶ騾・・繝・メ繝ｳ繧ｰ縲ゆｸ贋ｽ・譯井ｻｶ繧定ｿ斐☆"""
    system = '''SES reverse matching AI. Given one engineer, find matching job projects. Reply JSON only.
Score each project 0-100 based on skill match and price fit.
Return top matches sorted by score descending.
{"matches":[{
  "project_name":"",
  "project_price":0,
  "score":0,
  "required_match":{"Java":true},
  "optional_match":{},
  "gross_profit":0,
  "note":""
}]}'''
    result = call_claude(system, json.dumps({"engineer": engineer, "projects": projects}, ensure_ascii=False), max_tokens=2000)
    try:
        result_obj = json.loads(re.sub(r'```json|```', '', result).strip())
        if not isinstance(result_obj, dict):
            return {"matches": []}
        return result_obj
    except Exception as e:
        print(f"[run_reverse_matching] parse error: {e}")
        return {"matches": []}


def evaluate_candidate(candidate, project_price):
    """OK/NG繧貞愛螳壹＠縺ｦNG逅・罰縺ｨ笳凝苓ｩｳ邏ｰ繧定ｿ斐☆"""
    ng_reasons = []
    cp = normalize_price(candidate.get("price", 0)) or 0
    pp = project_price or 0

    if cp == 0:
        ng_reasons.append("蜊倅ｾ｡荳肴・")
    elif pp > 0:
        diff = pp - cp
        if diff < 5:
            ng_reasons.append(f"邊怜茜{diff}荳・ｼ亥渕貅・荳・悴貅・・)

    required_match = candidate.get("required_match", {})
    missing = [k for k, v in required_match.items() if not v]
    if missing:
        ng_reasons.append(f"蠢・暗・ {', '.join(missing)}")

    is_ok = len(ng_reasons) == 0

    req_str = " ".join(f"{'笳・ if v else 'ﾃ・}{k}" for k, v in required_match.items()) if required_match else ""
    opt_match = candidate.get("optional_match", {})
    opt_str = " ".join(f"{'笳・ if v else '笆ｳ'}{k}" for k, v in opt_match.items()) if opt_match else ""

    detail_parts = []
    if req_str: detail_parts.append(f"蠢・・ {req_str}")
    if opt_str: detail_parts.append(f"蟆壼庄: {opt_str}")

    return is_ok, ng_reasons, " / ".join(detail_parts)


def build_matching_message(proj_name, ok_candidates, ng_candidates, proposal_draft):
    msg = f"笨・譯井ｻｶ縲鶏proj_name}縲咲匳骭ｲ繝ｻ繝槭ャ繝√Φ繧ｰ螳御ｺ・n\n"

    if ok_candidates:
        msg += f"縲絶怛 OK蛟呵｣・{len(ok_candidates)}蜷阪曾n"
        for i, (c, detail) in enumerate(ok_candidates, 1):
            price = normalize_price(c.get("price", 0)) or 0
            msg += f"{i}. {c['name']} / {price}荳・・\n"
            if detail: msg += f"   {detail}\n"
    else:
        msg += "縲絶怛 OK蛟呵｣懊代↑縺予n"

    if ng_candidates:
        msg += f"\n縲絶無 蜿り・呵｣・{len(ng_candidates)}蜷阪曾n"
        for i, (c, ng_reasons, detail) in enumerate(ng_candidates, 1):
            price = normalize_price(c.get("price", 0)) or 0
            msg += f"{i}. {c['name']} / {price}荳・・\n"
            msg += f"   笞・・{' / '.join(ng_reasons)}\n"
            if detail: msg += f"   {detail}\n"

    if proposal_draft:
        msg += f"\n謠先｡域枚:\n{proposal_draft[:800]}"

    msg += "\n\n"
    if ok_candidates and ng_candidates:
        msg += "縲碁∽ｿ｡縺励※ [繝｡繧｢繝云縲坂・ OK蛟呵｣懊・縺ｿ\n縲娯無繧ょ性繧√※騾∽ｿ｡縺励※ [繝｡繧｢繝云縲坂・ 蜈ｨ蜩｡"
    elif ok_candidates:
        msg += "縲碁∽ｿ｡縺励※ [繝｡繧｢繝云縲阪〒諢丞髄遒ｺ隱阪Γ繝ｼ繝ｫ繧帝√ｊ縺ｾ縺・
    else:
        msg += "縲娯無繧ょ性繧√※騾∽ｿ｡縺励※ [繝｡繧｢繝云縲阪〒蜿り・呵｣懊ｒ騾√ｌ縺ｾ縺・

    return msg


def build_reverse_match_message(eng_name, matches):
    """騾・・繝・メ繝ｳ繧ｰ邨先棡縺ｮLINE繝｡繝・そ繝ｼ繧ｸ繧堤ｵ・∩遶九※繧・""
    if not matches:
        return f"笨・逋ｻ骭ｲ螳御ｺ・ {eng_name}\n\n笞・・繝槭ャ繝√☆繧句供髮・ｸｭ譯井ｻｶ縺ｪ縺・

    msg = f"笨・逋ｻ骭ｲ螳御ｺ・ {eng_name}\n\n縲舌・繝・メ縺吶ｋ譯井ｻｶ {len(matches)}莉ｶ縲曾n"
    for i, m in enumerate(matches[:3], 1):
        pname = m.get("project_name", "荳肴・")
        pprice = m.get("project_price", 0)
        gross = m.get("gross_profit", 0)
        score = m.get("score", 0)
        req_match = m.get("required_match", {})
        req_str = " ".join(f"{'笳・ if v else 'ﾃ・}{k}" for k, v in req_match.items()) if req_match else ""

        msg += f"\n{i}. {pname}\n"
        msg += f"   譯井ｻｶ蜊倅ｾ｡: {pprice}荳・・ / 邊怜茜隕玖ｾｼ: {gross}荳・・ / 繧ｹ繧ｳ繧｢: {score}\n"
        if req_str: msg += f"   蠢・・ {req_str}\n"

    if len(matches) > 3:
        msg += f"\n...莉本len(matches)-3}莉ｶ"

    return msg



def run_double_check(proposal_text, candidates_info):
    """繝繝悶Ν繝√ぉ繝・けAI: 騾∽ｿ｡蜑阪↓謠先｡域枚繧呈､懆ｨｼ繝ｻ閾ｪ蜍穂ｿｮ豁｣縺吶ｋ"""
    system = """SES proposal double-checker. Reply JSON only.
Check for:
1. Forbidden words: 蜈・ｶｳ, 蜊ｳ謌ｦ蜉・ 蠑顔､ｾ, 蠖鍋､ｾ
2. Wrong honorifics: 謨吶∴縺ｦ縺上□縺輔＞->縺疲蕗謗医￥縺縺輔＞, 縺企｡倥＞縺励∪縺・>繧医ｍ縺励￥縺企｡倥＞縺・◆縺励∪縺・
3. Unmasked company/person names in proposal body
Return: {"ok": true, "issues": [], "corrected": "same as input if ok"}
If issues found, return corrected text with fixes applied."""

    payload = str({"proposal": proposal_text[:1000], "candidates": candidates_info})
    import json as _json
    result = call_claude(system, _json.dumps({"proposal": proposal_text[:1000], "candidates": candidates_info}, ensure_ascii=False), max_tokens=1000)
    try:
        result_obj = _json.loads(re.sub(r'```json|```', '', result).strip())
        if not isinstance(result_obj, dict):
            return True, [], proposal_text
        return result_obj.get("ok", True), result_obj.get("issues", []), result_obj.get("corrected", proposal_text)
    except Exception as e:
        print(f"[run_double_check] parse error: {e}")
        return True, [], proposal_text

def notion_query(db_id, filter_obj=None):
    results, payload = [], {"page_size": 100}
    if filter_obj: payload["filter"] = filter_obj
    while True:
        r = requests.post(f"https://api.notion.com/v1/databases/{db_id}/query",
                         headers=NOTION_HEADERS, json=payload)
        data = r.json()
        results.extend(data.get("results", []))
        if not data.get("has_more"): break
        payload["start_cursor"] = data["next_cursor"]
    return results


def register_engineer(info, raw_text, sender):
    name = info.get("name") or "(no name)"
    note = f"[LINE auto-register: {sender}]\n{info.get('note', raw_text[:1500])}"
    props = {
        "蜷榊燕": {"title": [{"text": {"content": name}}]},
        "遞ｼ蜒咲憾豕・: {"select": {"name": "遞ｼ蜒榊庄閭ｽ"}},
        "蛯呵・ｼ・INE繝｡繝｢・・: {"rich_text": [{"text": {"content": note[:2000]}}]}
    }
    skills = [s for s in info.get("skills", []) if s in VALID_SKILLS]
    if skills: props["繧ｹ繧ｭ繝ｫ"] = {"multi_select": [{"name": s} for s in skills]}
    price_val = normalize_price(info.get("price", 0))
    if price_val: props["蜊倅ｾ｡・井ｸ・・・・] = {"number": price_val}
    if info.get("experience_years"): props["邨碁ｨ灘ｹｴ謨ｰ"] = {"number": info["experience_years"]}
    res = requests.post("https://api.notion.com/v1/pages", headers=NOTION_HEADERS,
                       json={"parent": {"database_id": NOTION_ENGINEER_DB_ID}, "properties": props})
    print(f"register_engineer status: {res.status_code}")
    if res.status_code == 200:
        return True, res.json()["id"]
    print(res.text[:300])
    return False, ""


def register_project(info, raw_text, sender):
    name = info.get("name") or "(no name)"
    note = f"[LINE auto-register: {sender}]\n{info.get('note', raw_text[:1500])}"
    props = {
        "譯井ｻｶ蜷・: {"title": [{"text": {"content": name}}]},
        "繧ｹ繝・・繧ｿ繧ｹ": {"select": {"name": "蜍滄寔荳ｭ"}},
        "譯井ｻｶ隧ｳ邏ｰ": {"rich_text": [{"text": {"content": note[:2000]}}]}
    }
    req = [s for s in info.get("required_skills", []) if s in VALID_SKILLS]
    opt = [s for s in info.get("optional_skills", []) if s in VALID_SKILLS]
    if req: props["蠢・ｦ√せ繧ｭ繝ｫ"] = {"multi_select": [{"name": s} for s in req]}
    if opt: props["蟆壼庄繧ｹ繧ｭ繝ｫ"] = {"multi_select": [{"name": s} for s in opt]}
    price_val = normalize_price(info.get("price", 0))
    if price_val: props["蜊倅ｾ｡・井ｸ・・・・] = {"number": price_val}
    if info.get("location"): props["蜍､蜍吝慍"] = {"rich_text": [{"text": {"content": info["location"]}}]}
    if info.get("period"): props["譛滄俣"] = {"rich_text": [{"text": {"content": info["period"]}}]}
    res = requests.post("https://api.notion.com/v1/pages", headers=NOTION_HEADERS,
                       json={"parent": {"database_id": NOTION_PROJECT_DB_ID}, "properties": props})
    print(f"register_project status: {res.status_code}")
    if res.status_code == 200:
        return True, res.json()["id"]
    print(res.text[:300])
    return False, ""


def get_available_engineers():
    pages = notion_query(NOTION_ENGINEER_DB_ID, {
        "property": "遞ｼ蜒咲憾豕・, "select": {"equals": "遞ｼ蜒榊庄閭ｽ"}
    })
    result = []
    for p in pages:
        props = p["properties"]
        name_items = props.get("蜷榊燕", {}).get("title", [])
        name = name_items[0].get("plain_text", "unknown") if name_items else "unknown"
        skills = [o["name"] for o in props.get("繧ｹ繧ｭ繝ｫ", {}).get("multi_select", [])]
        price = props.get("蜊倅ｾ｡・井ｸ・・・・, {}).get("number", 0) or 0
        note_items = props.get("蛯呵・ｼ・INE繝｡繝｢・・, {}).get("rich_text", [])
        note = note_items[0].get("plain_text", "") if note_items else ""
        source = "unknown"
        if "line auto-register: matsuno" in note.lower(): source = "matsuno"
        elif "line auto-register: okamoto" in note.lower(): source = "okamoto"
        result.append({"name": name, "skills": skills, "price": price, "note": note[:300], "source": source})
    return result


def get_active_projects():
    """蜍滄寔荳ｭ譯井ｻｶ繧誰otion縺九ｉ蜿門ｾ・""
    pages = notion_query(NOTION_PROJECT_DB_ID, {
        "property": "繧ｹ繝・・繧ｿ繧ｹ", "select": {"equals": "蜍滄寔荳ｭ"}
    })
    result = []
    for p in pages:
        props = p["properties"]
        name_items = props.get("譯井ｻｶ蜷・, {}).get("title", [])
        name = name_items[0].get("plain_text", "unknown") if name_items else "unknown"
        req_skills = [o["name"] for o in props.get("蠢・ｦ√せ繧ｭ繝ｫ", {}).get("multi_select", [])]
        opt_skills = [o["name"] for o in props.get("蟆壼庄繧ｹ繧ｭ繝ｫ", {}).get("multi_select", [])]
        price = props.get("蜊倅ｾ｡・井ｸ・・・・, {}).get("number", 0) or 0
        location_items = props.get("蜍､蜍吝慍", {}).get("rich_text", [])
        location = location_items[0].get("plain_text", "") if location_items else ""
        result.append({
            "name": name,
            "required_skills": req_skills,
            "optional_skills": opt_skills,
            "price": price,
            "location": location,
        })
    return result


def send_email_via_callback(account, to_addr, subject, body):
    import smtplib, ssl
    from email.mime.text import MIMEText
    from email.header import Header as EmailHeader

    accounts_cfg = {
        'matsuno': {'user': 'r-matsuno@terra-ltd.co.jp', 'pw': os.environ.get('MATSUNO_MAIL_PASSWORD', os.environ.get('SESSALES_MAIL_PASSWORD', ''))},
        'okamoto': {'user': 'r-okamoto@terra-ltd.co.jp', 'pw': os.environ.get('OKAMOTO_MAIL_PASSWORD', os.environ.get('SESSALES_MAIL_PASSWORD', ''))},
        'sessales': {'user': 'sessales@terra-ltd.co.jp', 'pw': os.environ.get('SESSALES_MAIL_PASSWORD', '')},
    }
    acc = accounts_cfg.get(account, accounts_cfg['sessales'])
    user, pw = acc['user'], acc['pw']
    if not pw:
        print(f"[send_email] ERROR: パスワード未設定 account={account}")
        return False
    try:
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = EmailHeader(subject, 'utf-8')
        msg['From'] = user
        msg['To'] = to_addr
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL('mail65.onamae.ne.jp', 465, context=ctx) as s:
            s.login(user, pw)
            s.sendmail(user, [to_addr], msg.as_bytes())
        print(f"[send_email] SENT OK to={to_addr} from={user}")
        return True
    except Exception as e:
        print(f"[send_email] ERROR: {e}")
        return False

def reply_message(reply_token, text, token):
    if len(text) > 4900: text = text[:4900] + "\n...(truncated)"
    requests.post("https://api.line.me/v2/bot/message/reply",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"replyToken": reply_token, "messages": [{"type": "text", "text": text}]})


def push_message(user_id, text, token):
    if not user_id: return
    if len(text) > 4900: text = text[:4900] + "\n...(truncated)"
    requests.post("https://api.line.me/v2/bot/message/push",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"to": user_id, "messages": [{"type": "text", "text": text}]})


def handle_sheet_url(url, reply_token, sender, sender_token):
    reply_message(reply_token, "投 繧ｹ繝励Ξ繝・ラ繧ｷ繝ｼ繝医ｒ蜿門ｾ嶺ｸｭ...", sender_token)
    result = fetch_sheet_text(url)
    if result["status"] == "login_required":
        reply_message(reply_token, "笞・・繝ｭ繧ｰ繧､繝ｳ縺悟ｿ・ｦ√↑繧ｹ繝励Ξ繝・ラ繧ｷ繝ｼ繝医・縺溘ａ繧ｹ繧ｭ繝・・縺励∪縺励◆", sender_token)
        return
    elif result["status"] == "error":
        reply_message(reply_token, f"笶・繧ｹ繝励Ξ繝・ラ繧ｷ繝ｼ繝亥叙蠕怜､ｱ謨・ {result.get('error','')[:100]}", sender_token)
        return

    text = result.get("text", "")
    if not text or len(text.strip()) < 50:
        reply_message(reply_token, "笞・・繧ｹ繝励Ξ繝・ラ繧ｷ繝ｼ繝医・蜀・ｮｹ縺悟叙蠕励〒縺阪∪縺帙ｓ縺ｧ縺励◆", sender_token)
        return

    content_type = classify_sheet_content(text)
    raw_text = f"[繧ｹ繝励Ξ繝・ラ繧ｷ繝ｼ繝・ {url}]"

    if content_type == "project":
        projects = extract_projects_from_text(text)
        if not projects:
            reply_message(reply_token, "笞・・譯井ｻｶ諠・ｱ縺梧歓蜃ｺ縺ｧ縺阪∪縺帙ｓ縺ｧ縺励◆", sender_token)
            return
        success_count = skip_count = 0
        for proj in projects:
            ok, _ = register_project(proj, raw_text, sender)
            if ok: success_count += 1
            else: skip_count += 1
        msg = f"笨・繧ｹ繝励Ξ繝・ラ繧ｷ繝ｼ繝医°繧画｡井ｻｶ逋ｻ骭ｲ螳御ｺ・n\n逋ｻ骭ｲ: {success_count}莉ｶ / 繧ｹ繧ｭ繝・・: {skip_count}莉ｶ\n"
        for i, p in enumerate(projects[:5], 1):
            msg += f"{i}. {p.get('name','(no name)')} / {p.get('price',0)}荳・・\n"
        if len(projects) > 5: msg += f"...莉本len(projects)-5}莉ｶ"
        reply_message(reply_token, msg, sender_token)
    else:
        engineers = extract_engineers_from_text(text)
        if not engineers:
            reply_message(reply_token, "笞・・莠ｺ蜩｡諠・ｱ縺梧歓蜃ｺ縺ｧ縺阪∪縺帙ｓ縺ｧ縺励◆", sender_token)
            return
        success_count = skip_count = 0
        registered = []
        for eng in engineers:
            ok, _ = register_engineer(eng, raw_text, sender)
            if ok:
                success_count += 1
                registered.append(eng)
            else:
                skip_count += 1
        msg = f"笨・繧ｹ繝励Ξ繝・ラ繧ｷ繝ｼ繝医°繧我ｺｺ蜩｡逋ｻ骭ｲ螳御ｺ・n\n逋ｻ骭ｲ: {success_count}蜷・/ 繧ｹ繧ｭ繝・・: {skip_count}蜷構n"
        for i, e in enumerate(engineers[:5], 1):
            msg += f"{i}. {e.get('name','(no name)')} / {e.get('price',0)}荳・・\n"
        if len(engineers) > 5: msg += f"...莉本len(engineers)-5}蜷・
        # 隍・焚逋ｻ骭ｲ縺ｮ蝣ｴ蜷医・騾・・繝・メ繝ｳ繧ｰ繧偵∪縺ｨ繧√※螳滓命
        if registered:
            active_projects = get_active_projects()
            if active_projects:
                msg += f"\n\n庁 {len(registered)}蜷榊・縺ｮ騾・・繝・メ繝ｳ繧ｰ荳ｭ..."
                reply_message(reply_token, msg, sender_token)
                for eng in registered[:3]:  # 譛螟ｧ3蜷阪∪縺ｧ騾・・繝・メ繝ｳ繧ｰ
                    result_m = run_reverse_matching(eng, active_projects)
                    matches = result_m.get("matches", [])[:3]
                    if matches:
                        rev_msg = build_reverse_match_message(eng.get("name","?"), matches)
                        push_message(MATSUNO_USER_ID if sender == "matsuno" else OKAMOTO_USER_ID,
                                     rev_msg,
                                     MATSUNO_CHANNEL_TOKEN if sender == "matsuno" else OKAMOTO_CHANNEL_TOKEN)
                return
        reply_message(reply_token, msg, sender_token)


def process_message(text, reply_token, sender, sender_token):
    print(f"[{sender}] {text[:80]}")
    pending_key = sender + "_latest"
    text_stripped = text.strip()

    # 笏笏 騾∽ｿ｡謖・､ｺ縺ｮ蜃ｦ逅・笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏
    # 縲碁∽ｿ｡縺励※ xxx@yyy.com縲阪∪縺溘・縲娯無繧ょ性繧√※騾∽ｿ｡縺励※ xxx@yyy.com縲・
    is_send_all = "笆ｳ繧ょ性繧√※騾∽ｿ｡" in text_stripped or "笆ｳ蜷ｫ繧√※騾∽ｿ｡" in text_stripped
    is_send_ok  = text_stripped.startswith("騾∽ｿ｡縺励※") or text_stripped.startswith("騾∽ｿ｡ ")

    if is_send_ok or is_send_all:
        pending = PENDING_PROPOSALS.get(pending_key)
        if not pending:
            reply_message(reply_token, "笞・・騾∽ｿ｡蠕・■縺ｮ謠先｡医′縺ゅｊ縺ｾ縺帙ｓ", sender_token)
            return

        # 繝｡繧｢繝画歓蜃ｺ
        emails = EMAIL_PATTERN.findall(text_stripped)
        to_addr = emails[0] if emails else None

        ok_list  = pending.get("ok", [])
        ng_list  = pending.get("ng", [])
        draft    = pending.get("proposal_draft", "")
        proj_name = pending.get("proj_name", "譯井ｻｶ")

        target = ok_list + (ng_list if is_send_all else [])
        target_names = [c["name"] for c, *_ in target]

        if to_addr:
            # 螳滄圀縺ｫ繝｡繝ｼ繝ｫ騾∽ｿ｡
            account = "matsuno" if sender == "matsuno" else "okamoto"
            subject = f"縲舌＃謠先｡医捜proj_name}"
            body = draft if draft else f"縲舌＃謠先｡医捜proj_name}\n\n" + "\n".join(f"繝ｻ{n}" for n in target_names)
            sent = send_email_via_callback(account, to_addr, subject, body)
            if sent:
                reply_message(reply_token,
                    f"鐙 繝｡繝ｼ繝ｫ騾∽ｿ｡螳御ｺ・n螳帛・: {to_addr}\n莉ｶ蜷・ {subject}\n蟇ｾ雎｡: {len(target_names)}蜷・,
                    sender_token)
            else:
                # 繝輔か繝ｼ繝ｫ繝舌ャ繧ｯ: 譛ｬ譁・□縺題ｿ斐☆
                reply_message(reply_token,
                    f"笞・・閾ｪ蜍暮∽ｿ｡螟ｱ謨励ゆｻ･荳九ｒ繧ｳ繝斐・縺励※謇句虚騾∽ｿ｡縺励※縺上□縺輔＞縲・n螳帛・: {to_addr}\n\n{body[:1500]}",
                    sender_token)
        else:
            # 繝｡繧｢繝峨↑縺・竊・譛ｬ譁・□縺題ｿ斐☆
            label = "蜈ｨ蜩｡" if is_send_all else "OK蛟呵｣懊・縺ｿ"
            reply_message(reply_token,
                f"搭 謠先｡亥・螳ｹ・・label} {len(target_names)}蜷搾ｼ噂n騾∽ｿ｡蜈医Γ繧｢繝峨ｒ縲碁∽ｿ｡縺励※ xxx@yyy.com縲阪〒謖・ｮ壹＠縺ｦ縺上□縺輔＞\n\n{draft[:1500]}",
                sender_token)
            return  # pending縺ｯ菫晄戟

        del PENDING_PROPOSALS[pending_key]
        return

    # 笏笏 繧ｹ繝励Ξ繝・ラ繧ｷ繝ｼ繝・RL 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏
    sheet_urls = SHEET_URL_PATTERN.findall(text)
    if sheet_urls:
        handle_sheet_url(sheet_urls[0], reply_token, sender, sender_token)
        return

    # 笏笏 騾壼ｸｸ蛻・｡槫・逅・笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏
    info = classify_message(text)
    msg_type = info.get("type", "other")
    print(f"[type] {msg_type}")

    # 笏笏 莠ｺ蜩｡1蜷・笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏
    if msg_type == "engineer":
        success, _ = register_engineer(info, text, sender)
        if not success:
            reply_message(reply_token, "笶・逋ｻ骭ｲ螟ｱ謨・, sender_token)
            return

        # 騾・・繝・メ繝ｳ繧ｰ
        active_projects = get_active_projects()
        if not active_projects:
            name = info.get("name", "(no name)")
            skills_str = ", ".join(info.get("skills", [])) or "N/A"
            price = normalize_price(info.get("price", 0))
            reply_message(reply_token,
                f"笨・逋ｻ骭ｲ螳御ｺ・n蜷榊燕: {name}\n繧ｹ繧ｭ繝ｫ: {skills_str}\n蜊倅ｾ｡: {price}荳・・\n\n蜍滄寔荳ｭ譯井ｻｶ縺ｪ縺・,
                sender_token)
            return

        result_m = run_reverse_matching(info, active_projects)
        matches = result_m.get("matches", [])[:3]
        msg = build_reverse_match_message(info.get("name", "(no name)"), matches)
        reply_message(reply_token, msg, sender_token)

    # 笏笏 莠ｺ蜩｡隍・焚 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏
    elif msg_type == "engineers":
        engineers_list = info.get("engineers", [])
        if not engineers_list:
            reply_message(reply_token, "笶・莠ｺ蜩｡諠・ｱ縺悟叙蠕励〒縺阪∪縺帙ｓ縺ｧ縺励◆", sender_token)
            return
        success_count = skip_count = 0
        registered = []
        for eng in engineers_list:
            ok, _ = register_engineer(eng, text, sender)
            if ok:
                success_count += 1
                registered.append(eng)
            else:
                skip_count += 1
        msg = f"笨・隍・焚莠ｺ蜩｡逋ｻ骭ｲ螳御ｺ・n逋ｻ骭ｲ: {success_count}蜷・/ 繧ｹ繧ｭ繝・・: {skip_count}蜷構n"
        for i, e in enumerate(engineers_list[:5], 1):
            msg += f"{i}. {e.get('name','(no name)')} / {e.get('price',0)}荳・・\n"
        reply_message(reply_token, msg, sender_token)
        # 騾・・繝・メ繝ｳ繧ｰ繧帝撼蜷梧悄逧・↓push・域怙螟ｧ3蜷搾ｼ・
        active_projects = get_active_projects()
        if active_projects and registered:
            uid = MATSUNO_USER_ID if sender == "matsuno" else OKAMOTO_USER_ID
            tok = MATSUNO_CHANNEL_TOKEN if sender == "matsuno" else OKAMOTO_CHANNEL_TOKEN
            for eng in registered[:3]:
                rm = run_reverse_matching(eng, active_projects)
                matches = rm.get("matches", [])[:3]
                if matches:
                    push_message(uid, build_reverse_match_message(eng.get("name","?"), matches), tok)

    # 笏笏 譯井ｻｶ1莉ｶ 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏
    elif msg_type == "project":
        success, _ = register_project(info, text, sender)
        proj_name = info.get("name", "project")
        if not success:
            reply_message(reply_token, "笶・譯井ｻｶ逋ｻ骭ｲ螟ｱ謨・, sender_token)
            return

        engineers = get_available_engineers()
        matching = run_matching(info, engineers)
        all_candidates = matching.get("candidates", [])
        project_price = normalize_price(info.get("price", 0)) or 0
        proposal_draft = matching.get("proposal_draft", "")

        ok_candidates, ng_candidates = [], []
        for c in all_candidates:
            is_ok, ng_reasons, detail_str = evaluate_candidate(c, project_price)
            if is_ok: ok_candidates.append((c, detail_str))
            else: ng_candidates.append((c, ng_reasons, detail_str))

        PENDING_PROPOSALS[pending_key] = {
            "ok": ok_candidates,
            "ng": ng_candidates,
            "proposal_draft": proposal_draft,
            "proj_name": proj_name,
        }

        msg = build_matching_message(proj_name, ok_candidates, ng_candidates, proposal_draft)
        reply_message(reply_token, msg, sender_token)

    # 笏笏 譯井ｻｶ隍・焚 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏
    elif msg_type == "projects":
        projects_list = info.get("projects", [])
        if not projects_list:
            reply_message(reply_token, "笶・譯井ｻｶ諠・ｱ縺悟叙蠕励〒縺阪∪縺帙ｓ縺ｧ縺励◆", sender_token)
            return
        success_count = skip_count = 0
        for proj in projects_list:
            ok, _ = register_project(proj, text, sender)
            if ok: success_count += 1
            else: skip_count += 1
        msg = f"笨・隍・焚譯井ｻｶ逋ｻ骭ｲ螳御ｺ・n逋ｻ骭ｲ: {success_count}莉ｶ / 繧ｹ繧ｭ繝・・: {skip_count}莉ｶ\n"
        for i, p in enumerate(projects_list[:5], 1):
            msg += f"{i}. {p.get('name','(no name)')} / {p.get('price',0)}荳・・\n"
        reply_message(reply_token, msg, sender_token)

    else:
        print(f"[other] ignored: {text[:50]}")


def handle_webhook(channel_secret, channel_token, sender_name):
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data()
    if not verify_signature(body, signature, channel_secret):
        abort(400)
    events = request.json.get('events', [])
    for event in events:
        if event['type'] != 'message' or event['message']['type'] != 'text':
            continue
        user_id = event.get('source', {}).get('userId', '')
        global MATSUNO_USER_ID
        if sender_name == "matsuno" and user_id and not MATSUNO_USER_ID:
            MATSUNO_USER_ID = user_id
            if os.path.exists(ENV_PATH):
                set_key(ENV_PATH, "MATSUNO_LINE_USER_ID", user_id)
        try:
            process_message(event['message']['text'], event['replyToken'], sender_name, channel_token)
        except Exception as e:
            print(f"Error [{sender_name}]: {e}")
            traceback.print_exc()
    return 'OK', 200


@app.route('/webhook', methods=['POST'])
def webhook_matsuno():
    return handle_webhook(MATSUNO_CHANNEL_SECRET, MATSUNO_CHANNEL_TOKEN, "matsuno")

@app.route('/webhook_okamoto', methods=['POST'])
def webhook_okamoto():
    return handle_webhook(OKAMOTO_CHANNEL_SECRET, OKAMOTO_CHANNEL_TOKEN, "okamoto")

@app.route('/health', methods=['GET'])
def health():
    return 'OK', 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

