"""
LINE Webhook Server v10
- 人員登録時に既存募集中案件と逆マッチング
- 「送信して [メアド]」でses-mail経由の実メール送信
- NG候補を○×付きで参考表示、△も含めて送信に対応
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

# ses-mail APIエンドポイント（Claude Desktop MCP経由ではなくローカルサーバー直接呼び出し）
# Railway上ではses-mailは使えないため、送信指示はローカルへのコールバック方式で別途対応
# → 現状は「送信内容をLINEに返す」＋「松野がses-mailで手動送信」フロー
# TODO: Railway→ローカルサーバーへのコールバック実装後に自動化

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

# 送信待ち提案を一時保存
# key: sender+"_latest" → {"ok": [...], "ng": [...], "proposal_draft": "", "proj_name": ""}
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
IMPORTANT: Ignore forwarding remarks (e.g. "これどうですか", "原さんどうですか") and extract only actual job/engineer info.
IMPORTANT: price field must be in 万円 unit as integer. e.g. "65万"->65, "45万～50万"->47 (midpoint), "650,000円"->65.

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
        sys.path.insert(0, r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_attachment_importer')
        from sheet_fetcher import fetch_sheet_text as _fetch
        return _fetch(url)
    except Exception as e:
        return {"status": "error", "error": str(e)}


def extract_engineers_from_text(text):
    try:
        import sys
        sys.path.insert(0, r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_attachment_importer')
        from ai_extractor import extract_engineers
        return extract_engineers(text, "sheet_from_line")
    except Exception as e:
        return []


def extract_projects_from_text(text):
    try:
        import sys
        sys.path.insert(0, r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_attachment_importer')
        from ai_extractor import extract_projects
        return extract_projects(text, "sheet_from_line")
    except Exception as e:
        return []


def run_matching(project, engineers):
    """案件 → 人員マッチング"""
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
    """人員 → 案件逆マッチング。上位3案件を返す"""
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
    """OK/NGを判定してNG理由と○×詳細を返す"""
    ng_reasons = []
    cp = normalize_price(candidate.get("price", 0)) or 0
    pp = project_price or 0

    if cp == 0:
        ng_reasons.append("単価不明")
    elif pp > 0:
        diff = pp - cp
        if diff < 5:
            ng_reasons.append(f"粗利{diff}万（基準5万未満）")

    required_match = candidate.get("required_match", {})
    missing = [k for k, v in required_match.items() if not v]
    if missing:
        ng_reasons.append(f"必須×: {', '.join(missing)}")

    is_ok = len(ng_reasons) == 0

    req_str = " ".join(f"{'○' if v else '×'}{k}" for k, v in required_match.items()) if required_match else ""
    opt_match = candidate.get("optional_match", {})
    opt_str = " ".join(f"{'○' if v else '△'}{k}" for k, v in opt_match.items()) if opt_match else ""

    detail_parts = []
    if req_str: detail_parts.append(f"必須: {req_str}")
    if opt_str: detail_parts.append(f"尚可: {opt_str}")

    return is_ok, ng_reasons, " / ".join(detail_parts)


def build_matching_message(proj_name, ok_candidates, ng_candidates, proposal_draft):
    msg = f"✅ 案件「{proj_name}」登録・マッチング完了\n\n"

    if ok_candidates:
        msg += f"【✅ OK候補 {len(ok_candidates)}名】\n"
        for i, (c, detail) in enumerate(ok_candidates, 1):
            price = normalize_price(c.get("price", 0)) or 0
            msg += f"{i}. {c['name']} / {price}万円\n"
            if detail: msg += f"   {detail}\n"
    else:
        msg += "【✅ OK候補】なし\n"

    if ng_candidates:
        msg += f"\n【△ 参考候補 {len(ng_candidates)}名】\n"
        for i, (c, ng_reasons, detail) in enumerate(ng_candidates, 1):
            price = normalize_price(c.get("price", 0)) or 0
            msg += f"{i}. {c['name']} / {price}万円\n"
            msg += f"   ⚠️ {' / '.join(ng_reasons)}\n"
            if detail: msg += f"   {detail}\n"

    if proposal_draft:
        msg += f"\n提案文:\n{proposal_draft[:800]}"

    msg += "\n\n"
    if ok_candidates and ng_candidates:
        msg += "「送信して [メアド]」→ OK候補のみ\n「△も含めて送信して [メアド]」→ 全員"
    elif ok_candidates:
        msg += "「送信して [メアド]」で意向確認メールを送ります"
    else:
        msg += "「△も含めて送信して [メアド]」で参考候補を送れます"

    return msg


def build_reverse_match_message(eng_name, matches):
    """逆マッチング結果のLINEメッセージを組み立てる"""
    if not matches:
        return f"✅ 登録完了: {eng_name}\n\n⚠️ マッチする募集中案件なし"

    msg = f"✅ 登録完了: {eng_name}\n\n【マッチする案件 {len(matches)}件】\n"
    for i, m in enumerate(matches[:3], 1):
        pname = m.get("project_name", "不明")
        pprice = m.get("project_price", 0)
        gross = m.get("gross_profit", 0)
        score = m.get("score", 0)
        req_match = m.get("required_match", {})
        req_str = " ".join(f"{'○' if v else '×'}{k}" for k, v in req_match.items()) if req_match else ""

        msg += f"\n{i}. {pname}\n"
        msg += f"   案件単価: {pprice}万円 / 粗利見込: {gross}万円 / スコア: {score}\n"
        if req_str: msg += f"   必須: {req_str}\n"

    if len(matches) > 3:
        msg += f"\n...他{len(matches)-3}件"

    return msg



def run_double_check(proposal_text, candidates_info):
    """ダブルチェックAI: 送信前に提案文を検証・自動修正する"""
    system = """SES proposal double-checker. Reply JSON only.
Check for:
1. Forbidden words: 充足, 即戦力, 弊社, 当社
2. Wrong honorifics: 教えてください->ご教授ください, お願いします->よろしくお願いいたします
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
        "名前": {"title": [{"text": {"content": name}}]},
        "稼働状況": {"select": {"name": "稼働可能"}},
        "備考（LINEメモ）": {"rich_text": [{"text": {"content": note[:2000]}}]}
    }
    skills = [s for s in info.get("skills", []) if s in VALID_SKILLS]
    if skills: props["スキル"] = {"multi_select": [{"name": s} for s in skills]}
    price_val = normalize_price(info.get("price", 0))
    if price_val: props["単価（万円）"] = {"number": price_val}
    if info.get("experience_years"): props["経験年数"] = {"number": info["experience_years"]}
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
        "案件名": {"title": [{"text": {"content": name}}]},
        "ステータス": {"select": {"name": "募集中"}},
        "案件詳細": {"rich_text": [{"text": {"content": note[:2000]}}]}
    }
    req = [s for s in info.get("required_skills", []) if s in VALID_SKILLS]
    opt = [s for s in info.get("optional_skills", []) if s in VALID_SKILLS]
    if req: props["必要スキル"] = {"multi_select": [{"name": s} for s in req]}
    if opt: props["尚可スキル"] = {"multi_select": [{"name": s} for s in opt]}
    price_val = normalize_price(info.get("price", 0))
    if price_val: props["単価（万円）"] = {"number": price_val}
    if info.get("location"): props["勤務地"] = {"rich_text": [{"text": {"content": info["location"]}}]}
    if info.get("period"): props["期間"] = {"rich_text": [{"text": {"content": info["period"]}}]}
    res = requests.post("https://api.notion.com/v1/pages", headers=NOTION_HEADERS,
                       json={"parent": {"database_id": NOTION_PROJECT_DB_ID}, "properties": props})
    print(f"register_project status: {res.status_code}")
    if res.status_code == 200:
        return True, res.json()["id"]
    print(res.text[:300])
    return False, ""


def get_available_engineers():
    pages = notion_query(NOTION_ENGINEER_DB_ID, {
        "property": "稼働状況", "select": {"equals": "稼働可能"}
    })
    result = []
    for p in pages:
        props = p["properties"]
        name_items = props.get("名前", {}).get("title", [])
        name = name_items[0].get("plain_text", "unknown") if name_items else "unknown"
        skills = [o["name"] for o in props.get("スキル", {}).get("multi_select", [])]
        price = props.get("単価（万円）", {}).get("number", 0) or 0
        note_items = props.get("備考（LINEメモ）", {}).get("rich_text", [])
        note = note_items[0].get("plain_text", "") if note_items else ""
        source = "unknown"
        if "line auto-register: matsuno" in note.lower(): source = "matsuno"
        elif "line auto-register: okamoto" in note.lower(): source = "okamoto"
        result.append({"name": name, "skills": skills, "price": price, "note": note[:300], "source": source})
    return result


def get_active_projects():
    """募集中案件をNotionから取得"""
    pages = notion_query(NOTION_PROJECT_DB_ID, {
        "property": "ステータス", "select": {"equals": "募集中"}
    })
    result = []
    for p in pages:
        props = p["properties"]
        name_items = props.get("案件名", {}).get("title", [])
        name = name_items[0].get("plain_text", "unknown") if name_items else "unknown"
        req_skills = [o["name"] for o in props.get("必要スキル", {}).get("multi_select", [])]
        opt_skills = [o["name"] for o in props.get("尚可スキル", {}).get("multi_select", [])]
        price = props.get("単価（万円）", {}).get("number", 0) or 0
        location_items = props.get("勤務地", {}).get("rich_text", [])
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
    """
    ローカルのjobz-commandサーバー経由でses-mailを呼び出す。
    Railwayから直接ses-mailは呼べないため、jobz-commandのHTTPサーバーに
    Pythonコードを実行させる方式。
    """
    import json as _json
    # jobz-commandサーバーにPythonスクリプトを送信して実行
    code = f"""
import sys
sys.path.insert(0, r'C:\\\\Users\\\\ma_py\\\\OneDrive\\\\デスクトップ\\\\ses_work\\\\mail_mcp')
# ses-mail MCPは直接Pythonから呼べないため、smtplibで直接送信
import smtplib, ssl, os
from email.mime.text import MIMEText
from email.header import Header
from dotenv import load_dotenv
load_dotenv(r'C:\\\\Users\\\\ma_py\\\\OneDrive\\\\デスクトップ\\\\ses_work\\\\config\\\\.env')

accounts = {{
    'matsuno': {{'user': 'r-matsuno@terra-ltd.co.jp', 'pw_key': 'MATSUNO_MAIL_PASSWORD'}},
    'okamoto': {{'user': 'r-okamoto@terra-ltd.co.jp', 'pw_key': 'OKAMOTO_MAIL_PASSWORD'}},
    'sessales': {{'user': 'sessales@terra-ltd.co.jp', 'pw_key': 'SESSALES_MAIL_PASSWORD'}},
}}
acc = accounts.get('{account}', accounts['sessales'])
user = acc['user']
pw = os.environ.get(acc['pw_key'], os.environ.get('SESSALES_MAIL_PASSWORD', ''))

msg = MIMEText({_json.dumps(body)}, 'plain', 'utf-8')
msg['Subject'] = Header({_json.dumps(subject)}, 'utf-8')
msg['From'] = user
msg['To'] = {_json.dumps(to_addr)}

ctx = ssl.create_default_context()
with smtplib.SMTP_SSL('mail65.onamae.ne.jp', 465, context=ctx) as s:
    s.login(user, pw)
    s.sendmail(user, [{_json.dumps(to_addr)}], msg.as_bytes())
print('SENT OK')
"""
    try:
        res = requests.post(
            "http://127.0.0.1:8765/run",
            headers={"X-Auth-Token": "jobz-terra-2026", "Content-Type": "application/json"},
            json={"cmd": f"python -c \"{code.replace(chr(10), ';').replace('\"', chr(39))}\""},
            timeout=30
        )
        if res.status_code == 200:
            output = res.json().get("stdout", "")
            return "SENT OK" in output
    except Exception as e:
        print(f"[send_email_via_callback] error: {e}")
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
    reply_message(reply_token, "📊 スプレッドシートを取得中...", sender_token)
    result = fetch_sheet_text(url)
    if result["status"] == "login_required":
        reply_message(reply_token, "⚠️ ログインが必要なスプレッドシートのためスキップしました", sender_token)
        return
    elif result["status"] == "error":
        reply_message(reply_token, f"❌ スプレッドシート取得失敗: {result.get('error','')[:100]}", sender_token)
        return

    text = result.get("text", "")
    if not text or len(text.strip()) < 50:
        reply_message(reply_token, "⚠️ スプレッドシートの内容が取得できませんでした", sender_token)
        return

    content_type = classify_sheet_content(text)
    raw_text = f"[スプレッドシート: {url}]"

    if content_type == "project":
        projects = extract_projects_from_text(text)
        if not projects:
            reply_message(reply_token, "⚠️ 案件情報が抽出できませんでした", sender_token)
            return
        success_count = skip_count = 0
        for proj in projects:
            ok, _ = register_project(proj, raw_text, sender)
            if ok: success_count += 1
            else: skip_count += 1
        msg = f"✅ スプレッドシートから案件登録完了\n\n登録: {success_count}件 / スキップ: {skip_count}件\n"
        for i, p in enumerate(projects[:5], 1):
            msg += f"{i}. {p.get('name','(no name)')} / {p.get('price',0)}万円\n"
        if len(projects) > 5: msg += f"...他{len(projects)-5}件"
        reply_message(reply_token, msg, sender_token)
    else:
        engineers = extract_engineers_from_text(text)
        if not engineers:
            reply_message(reply_token, "⚠️ 人員情報が抽出できませんでした", sender_token)
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
        msg = f"✅ スプレッドシートから人員登録完了\n\n登録: {success_count}名 / スキップ: {skip_count}名\n"
        for i, e in enumerate(engineers[:5], 1):
            msg += f"{i}. {e.get('name','(no name)')} / {e.get('price',0)}万円\n"
        if len(engineers) > 5: msg += f"...他{len(engineers)-5}名"
        # 複数登録の場合は逆マッチングをまとめて実施
        if registered:
            active_projects = get_active_projects()
            if active_projects:
                msg += f"\n\n💡 {len(registered)}名分の逆マッチング中..."
                reply_message(reply_token, msg, sender_token)
                for eng in registered[:3]:  # 最大3名まで逆マッチング
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

    # ── 送信指示の処理 ──────────────────────────────
    # 「送信して xxx@yyy.com」または「△も含めて送信して xxx@yyy.com」
    is_send_all = "△も含めて送信" in text_stripped or "△含めて送信" in text_stripped
    is_send_ok  = text_stripped.startswith("送信して") or text_stripped.startswith("送信 ")

    if is_send_ok or is_send_all:
        pending = PENDING_PROPOSALS.get(pending_key)
        if not pending:
            reply_message(reply_token, "⚠️ 送信待ちの提案がありません", sender_token)
            return

        # メアド抽出
        emails = EMAIL_PATTERN.findall(text_stripped)
        to_addr = emails[0] if emails else None

        ok_list  = pending.get("ok", [])
        ng_list  = pending.get("ng", [])
        draft    = pending.get("proposal_draft", "")
        proj_name = pending.get("proj_name", "案件")

        target = ok_list + (ng_list if is_send_all else [])
        target_names = [c["name"] for c, *_ in target]

        if to_addr:
            # 実際にメール送信
            account = "matsuno" if sender == "matsuno" else "okamoto"
            subject = f"【ご提案】{proj_name}"
            body = draft if draft else f"【ご提案】{proj_name}\n\n" + "\n".join(f"・{n}" for n in target_names)
            sent = send_email_via_callback(account, to_addr, subject, body)
            if sent:
                reply_message(reply_token,
                    f"📨 メール送信完了\n宛先: {to_addr}\n件名: {subject}\n対象: {len(target_names)}名",
                    sender_token)
            else:
                # フォールバック: 本文だけ返す
                reply_message(reply_token,
                    f"⚠️ 自動送信失敗。以下をコピーして手動送信してください。\n宛先: {to_addr}\n\n{body[:1500]}",
                    sender_token)
        else:
            # メアドなし → 本文だけ返す
            label = "全員" if is_send_all else "OK候補のみ"
            reply_message(reply_token,
                f"📋 提案内容（{label} {len(target_names)}名）\n送信先メアドを「送信して xxx@yyy.com」で指定してください\n\n{draft[:1500]}",
                sender_token)
            return  # pendingは保持

        del PENDING_PROPOSALS[pending_key]
        return

    # ── スプレッドシートURL ──────────────────────────
    sheet_urls = SHEET_URL_PATTERN.findall(text)
    if sheet_urls:
        handle_sheet_url(sheet_urls[0], reply_token, sender, sender_token)
        return

    # ── 通常分類処理 ────────────────────────────────
    info = classify_message(text)
    msg_type = info.get("type", "other")
    print(f"[type] {msg_type}")

    # ── 人員1名 ────────────────────────────────────
    if msg_type == "engineer":
        success, _ = register_engineer(info, text, sender)
        if not success:
            reply_message(reply_token, "❌ 登録失敗", sender_token)
            return

        # 逆マッチング
        active_projects = get_active_projects()
        if not active_projects:
            name = info.get("name", "(no name)")
            skills_str = ", ".join(info.get("skills", [])) or "N/A"
            price = normalize_price(info.get("price", 0))
            reply_message(reply_token,
                f"✅ 登録完了\n名前: {name}\nスキル: {skills_str}\n単価: {price}万円\n\n募集中案件なし",
                sender_token)
            return

        result_m = run_reverse_matching(info, active_projects)
        matches = result_m.get("matches", [])[:3]
        msg = build_reverse_match_message(info.get("name", "(no name)"), matches)
        reply_message(reply_token, msg, sender_token)

    # ── 人員複数 ───────────────────────────────────
    elif msg_type == "engineers":
        engineers_list = info.get("engineers", [])
        if not engineers_list:
            reply_message(reply_token, "❌ 人員情報が取得できませんでした", sender_token)
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
        msg = f"✅ 複数人員登録完了\n登録: {success_count}名 / スキップ: {skip_count}名\n"
        for i, e in enumerate(engineers_list[:5], 1):
            msg += f"{i}. {e.get('name','(no name)')} / {e.get('price',0)}万円\n"
        reply_message(reply_token, msg, sender_token)
        # 逆マッチングを非同期的にpush（最大3名）
        active_projects = get_active_projects()
        if active_projects and registered:
            uid = MATSUNO_USER_ID if sender == "matsuno" else OKAMOTO_USER_ID
            tok = MATSUNO_CHANNEL_TOKEN if sender == "matsuno" else OKAMOTO_CHANNEL_TOKEN
            for eng in registered[:3]:
                rm = run_reverse_matching(eng, active_projects)
                matches = rm.get("matches", [])[:3]
                if matches:
                    push_message(uid, build_reverse_match_message(eng.get("name","?"), matches), tok)

    # ── 案件1件 ────────────────────────────────────
    elif msg_type == "project":
        success, _ = register_project(info, text, sender)
        proj_name = info.get("name", "project")
        if not success:
            reply_message(reply_token, "❌ 案件登録失敗", sender_token)
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

    # ── 案件複数 ───────────────────────────────────
    elif msg_type == "projects":
        projects_list = info.get("projects", [])
        if not projects_list:
            reply_message(reply_token, "❌ 案件情報が取得できませんでした", sender_token)
            return
        success_count = skip_count = 0
        for proj in projects_list:
            ok, _ = register_project(proj, text, sender)
            if ok: success_count += 1
            else: skip_count += 1
        msg = f"✅ 複数案件登録完了\n登録: {success_count}件 / スキップ: {skip_count}件\n"
        for i, p in enumerate(projects_list[:5], 1):
            msg += f"{i}. {p.get('name','(no name)')} / {p.get('price',0)}万円\n"
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
