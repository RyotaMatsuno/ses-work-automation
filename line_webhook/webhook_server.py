"""

LINE Webhook Server v13

- スキルシートPDF/画像をLINEから受信してskill_reader_api（8766）で処理

"""



import os, hmac, hashlib, base64, json, re, traceback, threading, time

from datetime import date

from flask import Flask, request, abort

import requests

from dotenv import dotenv_values, set_key
try:
    from matching_logic import deduplicate_projects, build_reverse_match_message_v2
    MATCHING_LOGIC_AVAILABLE = True
except ImportError:
    MATCHING_LOGIC_AVAILABLE = False
    def deduplicate_projects(p): return p



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



app = Flask(__name__)

NOTION_HEADERS = {

    "Authorization": f"Bearer {NOTION_API_KEY}",

    "Content-Type": "application/json",

    "Notion-Version": "2022-06-28"

}

VALID_SKILLS = [
    "Java","Python","PHP","JavaScript","TypeScript","C#","C++","C","Go","Ruby",
    "Swift","Kotlin","R","COBOL","VB.NET","VBA","Scala","Rust","Perl","Bash",
    "React","Vue.js","Angular","Next.js","Nuxt.js","HTML","CSS","jQuery",
    "Node.js","Spring","Spring Boot","Django","Flask","Laravel","Rails",".NET",
    "Express","FastAPI",
    "AWS","GCP","Azure","Docker","Kubernetes","Terraform","Ansible","Linux",
    "Windows Server","VMware","OpenStack","Nginx","Apache",
    "MySQL","PostgreSQL","Oracle","SQL Server","MongoDB","Redis","Elasticsearch",
    "DynamoDB","Cassandra","SQLite",
    "Jenkins","GitLab","GitHub Actions","CircleCI","Git","Jira","Confluence",
    "Tableau","PowerBI","Spark","Hadoop","TensorFlow","PyTorch","scikit-learn",
    "Salesforce","SAP","ServiceNow","SharePoint","Power Apps","Power Automate",
    "CCNA","CCNP","Cisco","Fortinet","Zabbix","Prometheus",
    "FPGA","PLC","Unity","Android Studio","Xcode"
]



SHEET_URL_PATTERN = re.compile(r'https://docs\.google\.com/spreadsheets/[^\s]+')

EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')



PENDING_PROPOSALS = {}

# スキルシート解析結果の一時保存 key: sender+"_skill" → iko_mail text

PENDING_SKILL_MAIL = {}





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
    system = """You are an SES message classifier for a Japanese IT staffing company.
Reply JSON only. No markdown. No explanation.

Rules:
- price: man-yen integer. "65man"->65, "45-50man"->47, "650000yen"->65
- skills: normalize to English. C-plus-plus->C++, TypeScript->TypeScript
- location: extract city/ward. full-remote->full-remote
- available_date: YYYY-MM-DD or "sokujitsu"
- experience_years: integer estimate
- If forwarded message, extract only the embedded job/person info

Output ONE of these JSON shapes:

Single engineer: {"type":"engineer","name":"","skills":[],"price":0,"available_date":"","experience_years":0,"location":"","note":""}

Multiple engineers: {"type":"engineers","engineers":[...]}

Single job: {"type":"project","name":"","required_skills":[],"optional_skills":[],"price":0,"start_date":"","location":"","remote":"unknown","period":"","interview_count":0,"note":""}

Multiple jobs: {"type":"projects","projects":[...]}

Other: {"type":"other","note":""}

Examples:
Input: "Java/Spring 5nen, Tanaka, 65man, sokujitsu, Tokyo"
Output: {"type":"engineer","name":"Tanaka","skills":["Java","Spring Boot"],"price":65,"available_date":"sokujitsu","experience_years":5,"location":"Tokyo","note":""}

Input: "Kyuubo React TypeScript hissu, Next.js shoko, 55-60man, Shibuya shu3remote, 7gatsu"
Output: {"type":"project","name":"React/TypeScript case","required_skills":["React","TypeScript"],"optional_skills":["Next.js"],"price":57,"start_date":"2026-07-01","location":"Shibuya","remote":"shu3","period":"long","interview_count":1,"note":"kyuubo"}
"""
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

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'mail_attachment_importer'))

        from sheet_fetcher import fetch_sheet_text as _fetch

        return _fetch(url)

    except Exception as e:

        return {"status": "error", "error": str(e)}





def extract_engineers_from_text(text):

    try:

        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'mail_attachment_importer'))

        from ai_extractor import extract_engineers

        return extract_engineers(text, "sheet_from_line")

    except Exception as e:

        return []





def extract_projects_from_text(text):

    try:

        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'mail_attachment_importer'))

        from ai_extractor import extract_projects

        return extract_projects(text, "sheet_from_line")

    except Exception as e:

        return []





def run_matching(project, engineers):
    system = """SES matching AI. Reply JSON only. No markdown.

Business Rules:
- gross_profit = project_price - engineer_price (both in man-yen)
- gross < 5: NG reason "grori-fusoku"
- All required_skills must match: if any missing -> required_ok=false
- score 0-100: required match 60pts + optional match rate 20pts + gross quality 20pts (7man=100pct,5man=50pct)
- proposal_draft: formal Japanese business email. Use templates.
- FORBIDDEN in proposal: beshsa/toshsa -> remove, sokusenjryoku -> "match-do-takai-jinzai", oshiete-kudasai -> "gokyujyu-kudasai", jyuusoku -> "subete mitashite-ori"
- proposal format: list top candidates with single-line summary each

Output:
{"candidates":[{
  "name":"",
  "price":0,
  "available_date":"",
  "score":0,
  "gross_profit":0,
  "required_match":{"Java":true},
  "optional_match":{"Docker":true},
  "required_ok":true,
  "ng_reasons":[],
  "summary":""
}],"proposal_draft":""}
"""
    result = call_claude(system, json.dumps({"project": project, "engineers": engineers}, ensure_ascii=False), max_tokens=3000)
    try:
        result_obj = json.loads(re.sub(r'```json|```', '', result).strip())
        if not isinstance(result_obj, dict):
            return {"candidates": [], "proposal_draft": ""}
        return result_obj
    except Exception as e:
        print(f"[run_matching] parse error: {e}")
        return {"candidates": [], "proposal_draft": ""}


def run_reverse_matching(engineer, projects):
    system = """SES reverse matching AI. Reply JSON only. No markdown.

Rules:
- gross_profit = project_price - engineer_price
- ONLY include projects where gross_profit >= 5
- score 0-100: skill match 70pts + gross quality 30pts
- Sort by score desc, return top matches
- If engineer price unknown, estimate from experience

Output:
{"matches":[{
  "project_name":"",
  "project_price":0,
  "score":0,
  "gross_profit":0,
  "required_match":{"Java":true},
  "optional_match":{},
  "note":""
}]}
"""
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
    ng_reasons = list(candidate.get("ng_reasons", []))

    required_ok = candidate.get("required_ok", None)
    if required_ok is False:
        required_match = candidate.get("required_match", {})
        missing = [k for k, v in required_match.items() if not v]
        if missing:
            label = f"hissu-NG: {', '.join(missing)}"
            if label not in ng_reasons:
                ng_reasons.append(label)

    cp = normalize_price(candidate.get("price", 0)) or 0
    pp = normalize_price(project_price) or 0
    gross = candidate.get("gross_profit", 0)
    if gross == 0 and cp > 0 and pp > 0:
        gross = pp - cp
    if cp == 0:
        ng_reasons.append("tanka-mishettei")
    elif gross > 0 and gross < 5:
        ng_reasons.append(f"grori {gross}man (min 5man)")

    is_ok = len(ng_reasons) == 0

    required_match = candidate.get("required_match", {})
    req_str = " ".join(f"{'O' if v else 'X'}{k}" for k, v in required_match.items()) if required_match else ""
    opt_match = candidate.get("optional_match", {})
    opt_str = " ".join(f"{'O' if v else 'D'}{k}" for k, v in opt_match.items()) if opt_match else ""

    detail_parts = []
    if req_str: detail_parts.append(f"hissu: {req_str}")
    if opt_str: detail_parts.append(f"shoko: {opt_str}")

    return is_ok, ng_reasons, " / ".join(detail_parts)


def build_matching_message(proj_name, ok_candidates, ng_candidates, proposal_draft):

    msg = f"📊 案件『{proj_name}』登録・マッチング完了\n\n"



    if ok_candidates:

        msg += f"✅ OK候補: {len(ok_candidates)}名\n"

        for i, (c, detail) in enumerate(ok_candidates, 1):

            price = normalize_price(c.get("price", 0)) or 0

            msg += f"{i}. {c['name']} / {price}万\n"

            if detail: msg += f"   {detail}\n"

    else:

        msg += "✅ OK候補なし\n"



    if ng_candidates:

        msg += f"\n⚠️ 参考候補: {len(ng_candidates)}名\n"

        for i, (c, ng_reasons, detail) in enumerate(ng_candidates, 1):

            price = normalize_price(c.get("price", 0)) or 0

            msg += f"{i}. {c['name']} / {price}万\n"

            msg += f"   NG: {' / '.join(ng_reasons)}\n"

            if detail: msg += f"   {detail}\n"



    if proposal_draft:

        msg += f"\n提案文:\n{proposal_draft[:800]}"



    msg += "\n\n"

    if ok_candidates and ng_candidates:

        msg += "「送信して xxx@yyy.com」→ OK候補のみ\n「NGも含めて送信して xxx@yyy.com」→ 全員"

    elif ok_candidates:

        msg += "「送信して xxx@yyy.com」で意向確認メールを送ります"

    else:

        msg += "「NGも含めて送信して xxx@yyy.com」で参考候補を送れます"



    return msg





def build_reverse_match_message(eng_name, matches):

    if not matches:

        return f"📋 登録完了: {eng_name}\n\n⚠️ マッチする募集中案件なし"



    msg = f"📋 登録完了: {eng_name}\n\n🔎 マッチする案件 {len(matches)}件\n"

    for i, m in enumerate(matches[:3], 1):

        pname = m.get("project_name", "不明")

        pprice = m.get("project_price", 0)

        gross = m.get("gross_profit", 0)

        score = m.get("score", 0)

        req_match = m.get("required_match", {})

        req_str = " ".join(f"{'○' if v else '×'}{k}" for k, v in req_match.items()) if req_match else ""



        msg += f"\n{i}. {pname}\n"

        msg += f"   案件単価: {pprice}万 / 粗利予想: {gross}万 / スコア: {score}\n"

        if req_str: msg += f"   必須: {req_str}\n"



    if len(matches) > 3:

        msg += f"\n...他{len(matches)-3}件"



    return msg





def run_double_check(proposal_text, candidates_info):

    system = """SES proposal double-checker. Reply JSON only.

Check for:

1. Forbidden words: 弊社, 充足, 即戦力, 教えてください

2. Wrong honorifics

3. Unmasked company/person names in proposal body

Return: {"ok": true, "issues": [], "corrected": "same as input if ok"}

If issues found, return corrected text with fixes applied."""



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

        "ステータス": {"select": {"name": "稼働中"}},

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
    # 募集中・稼働中・選考中すべてをマッチング対象とする
    pages = notion_query(NOTION_PROJECT_DB_ID, {
        "or": [
            {"property": "ステータス", "select": {"equals": "募集中"}},
            {"property": "ステータス", "select": {"equals": "稼働中"}},
            {"property": "ステータス", "select": {"equals": "選考中"}}
        ]
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





def handle_file_message(message_id, mime_type, reply_token, sender, sender_token):

    """LINEから送られたPDF/画像ファイルをskill_reader_apiで処理"""

    try:

        # LINEからファイルコンテンツ取得

        token = MATSUNO_CHANNEL_TOKEN if sender == "matsuno" else OKAMOTO_CHANNEL_TOKEN

        res = requests.get(

            f"https://api-data.line.me/v2/bot/message/{message_id}/content",

            headers={"Authorization": f"Bearer {token}"},

            timeout=30

        )

        if res.status_code != 200:

            reply_message(reply_token, f"❌ ファイル取得失敗: {res.status_code}", sender_token)

            return



        b64_data = base64.b64encode(res.content).decode()



        # skill_reader_api（8766）に送信

        reply_message(reply_token, "📋 スキルシート解析中...", sender_token)

        api_res = requests.post(

            "http://127.0.0.1:8766/process_skill_sheet",

            json={"base64": b64_data, "mime": mime_type, "affiliation": "貴社"},

            timeout=120

        )



        if api_res.status_code != 200:

            reply_message(reply_token, f"❌ 解析失敗: {api_res.text[:200]}", sender_token)

            return



        result = api_res.json()

        if result.get("status") != "ok":

            reply_message(reply_token, f"❌ 解析エラー: {result.get('message','不明')}", sender_token)

            return



        eng = result.get("engineer", {})

        name = eng.get("name", "不明")

        skills = ", ".join(eng.get("skills", [])) or "なし"

        level = eng.get("level", "不明")

        summary = eng.get("summary", "")

        just_count = result.get("just_count", 0)

        iko_mail = result.get("iko_mail", "")



        # 結果をPENDING_SKILL_MAILに保存

        pending_key = sender + "_skill"

        PENDING_SKILL_MAIL[pending_key] = iko_mail



        msg = f"📋 スキルシート解析完了\n"

        msg += f"氏名: {name}\n"

        msg += f"レベル: {level}\n"

        msg += f"スキル: {skills}\n"

        if summary:

            msg += f"概要: {summary}\n"

        msg += f"\n粗利ジャスト案件（5〜12万）: {just_count}件\n"

        msg += "\n「メール送信して xxx@yyy.com」で意向確認メールを送信できます。"



        push_message(

            MATSUNO_USER_ID if sender == "matsuno" else OKAMOTO_USER_ID,

            msg,

            sender_token

        )



    except Exception as e:

        push_message(

            MATSUNO_USER_ID if sender == "matsuno" else OKAMOTO_USER_ID,

            f"❌ スキルシート処理エラー: {str(e)[:200]}",

            sender_token

        )

        traceback.print_exc()





def handle_sheet_url(url, reply_token, sender, sender_token):

    reply_message(reply_token, "🔄 スプレッドシートを取得中...", sender_token)

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

        msg = f"📊 スプレッドシートから案件登録完了\n\n登録: {success_count}件 / スキップ: {skip_count}件\n"

        for i, p in enumerate(projects[:5], 1):

            msg += f"{i}. {p.get('name','(no name)')} / {p.get('price',0)}万\n"

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

        msg = f"📊 スプレッドシートから人員登録完了\n\n登録: {success_count}名 / スキップ: {skip_count}名\n"

        for i, e in enumerate(engineers[:5], 1):

            msg += f"{i}. {e.get('name','(no name)')} / {e.get('price',0)}万\n"

        if len(engineers) > 5: msg += f"...他{len(engineers)-5}名"

        if registered:

            active_projects = deduplicate_projects(get_active_projects())

            if active_projects:

                msg += f"\n\n🔎 {len(registered)}名の逆マッチング中..."

                reply_message(reply_token, msg, sender_token)

                for eng in registered[:3]:

                    result_m = run_reverse_matching(eng, active_projects)

                    matches = result_m.get("matches", [])[:3]

                    if matches:
                        if MATCHING_LOGIC_AVAILABLE:
                            rev_msg = build_reverse_match_message_v2(
                                eng.get("name","?"), matches,
                                normalize_price(eng.get("price", 0)) or 0)
                        else:
                            rev_msg = build_reverse_match_message(eng.get("name","?"), matches)
                        push_message(MATSUNO_USER_ID if sender == "matsuno" else OKAMOTO_USER_ID,
                                     rev_msg,
                                     MATSUNO_CHANNEL_TOKEN if sender == "matsuno" else OKAMOTO_CHANNEL_TOKEN)

                return

        reply_message(reply_token, msg, sender_token)





def process_message(text, reply_token, sender, sender_token):

    print(f"[{sender}] {text[:80]}")

    pending_key = sender + "_latest"

    skill_key = sender + "_skill"

    text_stripped = text.strip()



    # ── 送信指示の処理 ───────────────────────────────────────────

    is_send_all = "NGも含めて送信" in text_stripped or "NG含めて送信" in text_stripped

    is_mail_send = "メール送信して" in text_stripped

    is_send_ok  = text_stripped.startswith("送信して") or text_stripped.startswith("送信 ")



    # スキルシート解析後の意向確認メール送信

    if is_mail_send and skill_key in PENDING_SKILL_MAIL:

        emails = EMAIL_PATTERN.findall(text_stripped)

        to_addr = emails[0] if emails else None

        iko_mail = PENDING_SKILL_MAIL[skill_key]

        if to_addr:

            account = "matsuno" if sender == "matsuno" else "okamoto"

            subject = "案件ご検討のお願い"

            sent = send_email_via_callback(account, to_addr, subject, iko_mail)

            if sent:

                reply_message(reply_token, f"✅ 意向確認メール送信完了\n送信先: {to_addr}", sender_token)

                del PENDING_SKILL_MAIL[skill_key]

            else:

                reply_message(reply_token, f"❌ 送信失敗。以下をコピーして手動送信してください:\n宛先: {to_addr}\n\n{iko_mail[:2000]}", sender_token)

        else:

            reply_message(reply_token, f"📧 送信先メールアドレスを指定してください\n例: メール送信して xxx@yyy.com\n\n{iko_mail[:1500]}", sender_token)

        return



    if is_send_ok or is_send_all:

        pending = PENDING_PROPOSALS.get(pending_key)

        if not pending:

            reply_message(reply_token, "⚠️ 送信待ちの提案がありません", sender_token)

            return



        emails = EMAIL_PATTERN.findall(text_stripped)

        to_addr = emails[0] if emails else None



        ok_list  = pending.get("ok", [])

        ng_list  = pending.get("ng", [])

        draft    = pending.get("proposal_draft", "")

        proj_name = pending.get("proj_name", "案件")



        target = ok_list + (ng_list if is_send_all else [])

        target_names = [c["name"] for c, *_ in target]



        if to_addr:

            account = "matsuno" if sender == "matsuno" else "okamoto"

            subject = f"【ご提案】{proj_name}"

            body = draft if draft else f"【ご提案】{proj_name}\n\n" + "\n".join(f"・{n}" for n in target_names)

            sent = send_email_via_callback(account, to_addr, subject, body)

            if sent:

                reply_message(reply_token,

                    f"✅ メール送信完了\n送信先: {to_addr}\n件名: {subject}\n対象: {len(target_names)}名",

                    sender_token)

            else:

                reply_message(reply_token,

                    f"❌ 自動送信失敗。以下をコピーして手動送信してください:\n送信先: {to_addr}\n\n{body[:1500]}",

                    sender_token)

        else:

            label = "全員" if is_send_all else "OK候補のみ"

            reply_message(reply_token,

                f"📋 提案内容確認（{label} {len(target_names)}名）\n送信先メールを「送信して xxx@yyy.com」で指定してください\n\n{draft[:1500]}",

                sender_token)

            return



        del PENDING_PROPOSALS[pending_key]

        return



    # ── スプレッドシートURL ──────────────────────────────────────

    sheet_urls = SHEET_URL_PATTERN.findall(text)

    if sheet_urls:

        handle_sheet_url(sheet_urls[0], reply_token, sender, sender_token)

        return



    # ── 通常メッセージ分類 ───────────────────────────────────────

    info = classify_message(text)

    msg_type = info.get("type", "other")

    print(f"[type] {msg_type}")



    if msg_type == "engineer":

        success, _ = register_engineer(info, text, sender)

        if not success:

            reply_message(reply_token, "❌ 登録失敗", sender_token)

            return

        active_projects = deduplicate_projects(get_active_projects())

        if not active_projects:

            name = info.get("name", "(no name)")

            skills_str = ", ".join(info.get("skills", [])) or "N/A"

            price = normalize_price(info.get("price", 0))

            reply_message(reply_token,

                f"📋 登録完了\n名前: {name}\nスキル: {skills_str}\n単価: {price}万\n\n稼働中案件なし",

                sender_token)

            return

        result_m = run_reverse_matching(info, active_projects)

        matches = result_m.get("matches", [])[:3]

        if MATCHING_LOGIC_AVAILABLE:
            msg = build_reverse_match_message_v2(
                info.get("name", "(no name)"), matches,
                normalize_price(info.get("price", 0)) or 0)
        else:
            msg = build_reverse_match_message(info.get("name", "(no name)"), matches)

        reply_message(reply_token, msg, sender_token)



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

        msg = f"📊 複数人員登録完了\n登録: {success_count}名 / スキップ: {skip_count}名\n"

        for i, e in enumerate(engineers_list[:5], 1):

            msg += f"{i}. {e.get('name','(no name)')} / {e.get('price',0)}万\n"

        reply_message(reply_token, msg, sender_token)

        active_projects = deduplicate_projects(get_active_projects())

        if active_projects and registered:

            uid = MATSUNO_USER_ID if sender == "matsuno" else OKAMOTO_USER_ID

            tok = MATSUNO_CHANNEL_TOKEN if sender == "matsuno" else OKAMOTO_CHANNEL_TOKEN

            for eng in registered[:3]:

                rm = run_reverse_matching(eng, active_projects)

                matches = rm.get("matches", [])[:3]

                if matches:

                    if MATCHING_LOGIC_AVAILABLE:
                        _rmsg = build_reverse_match_message_v2(
                            eng.get("name","?"), matches,
                            normalize_price(eng.get("price", 0)) or 0)
                    else:
                        _rmsg = build_reverse_match_message(eng.get("name","?"), matches)
                    push_message(uid, _rmsg, tok)



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

        msg = f"📊 複数案件登録完了\n登録: {success_count}件 / スキップ: {skip_count}件\n"

        for i, p in enumerate(projects_list[:5], 1):

            msg += f"{i}. {p.get('name','(no name)')} / {p.get('price',0)}万\n"

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

        event_type = event['type']

        if event_type != 'message':

            continue



        msg = event['message']

        msg_type = msg.get('type', '')

        reply_token = event['replyToken']

        user_id = event.get('source', {}).get('userId', '')



        global MATSUNO_USER_ID

        if sender_name == "matsuno" and user_id and not MATSUNO_USER_ID:

            MATSUNO_USER_ID = user_id

            if os.path.exists(ENV_PATH):

                set_key(ENV_PATH, "MATSUNO_LINE_USER_ID", user_id)



        try:

            if msg_type == 'text':

                process_message(msg['text'], reply_token, sender_name, channel_token)

            elif msg_type in ('image', 'file'):

                # PDF/画像スキルシート受信

                mime = msg.get('contentType', 'image/jpeg') if msg_type == 'image' else msg.get('fileName', '')

                # ファイル名からMIME判定

                if msg_type == 'file':

                    fname = msg.get('fileName', '').lower()

                    if fname.endswith('.pdf'):

                        mime = 'application/pdf'

                    elif fname.endswith('.docx'):

                        mime = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'

                    elif fname.endswith(('.png', '.jpg', '.jpeg')):

                        mime = f"image/{'png' if fname.endswith('.png') else 'jpeg'}"

                    else:

                        mime = 'application/octet-stream'

                handle_file_message(msg['id'], mime, reply_token, sender_name, channel_token)

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



def _keepalive():

    time.sleep(60)

    url = os.environ.get('RENDER_EXTERNAL_URL', 'https://ses-work-automation.onrender.com')

    while True:

        try:

            requests.get(f'{url}/health', timeout=10)

            print('[keepalive] ping OK')

        except Exception as e:

            print(f'[keepalive] ping failed: {e}')

        time.sleep(600)



threading.Thread(target=_keepalive, daemon=True).start()



if __name__ == '__main__':

    port = int(os.environ.get('PORT', 5000))

    app.run(host='0.0.0.0', port=port)

