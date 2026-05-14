"""
LINE Webhook Server v6
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
    """AIが万円単位を誤って円単位で返した場合に正規化する。
    100以上かつ100の倍数っぽい大きな値は万円換算とみなして割る。
    合理的な万円範囲: 30〜200万円
    """
    if price is None or price == 0:
        return price
    # 1000以上なら円単位と判断して万円に変換
    if price >= 1000:
        price = round(price / 10000)
    return price

def classify_message(text):
    system = 'SES business message classifier. Reply JSON only.\nIMPORTANT: Ignore any forwarding remarks (e.g. "これどうですか", "原さんどうですか" etc.) and extract only the actual job/engineer information.\nIMPORTANT: price field must be in 万円 unit as integer. e.g. "65万" or "65万円" -> 65, "70万" -> 70, "650,000円" -> 65. Never use raw yen values.\n\nengineer: {"type":"engineer","name":"","skills":[],"price":0,"available_date":"","experience_years":0,"note":""}\nproject: {"type":"project","name":"","required_skills":[],"optional_skills":[],"price":0,"start_date":"","location":"","remote":"unknown","period":"","note":""}\nother: {"type":"other","note":""}'
    result = call_claude(system, text, max_tokens=800)
    try:
        result_obj = json.loads(re.sub(r'```json|```', '', result).strip())
        if not isinstance(result_obj, dict):
            print(f"[classify_message] unexpected type: {type(result_obj)} -> fallback to other")
            return {"type": "other", "note": text[:300]}
        return result_obj
    except Exception as e:
        print(f"[classify_message] parse error: {e} / raw: {result[:100]}")
        return {"type": "other", "note": text[:300]}


def run_matching(project, engineers):
    system = 'SES matching AI. Reply JSON only.\n{"candidates":[{"name":"","price":0,"summary":"","required_match":{},"optional_match":{},"parallel":"none","engineer_source":"matsuno or okamoto or unknown"}],"proposal_draft":""}'
    result = call_claude(system, json.dumps({"project": project, "engineers": engineers}, ensure_ascii=False), max_tokens=2000)
    try:
        result_obj = json.loads(re.sub(r'```json|```', '', result).strip())
        if not isinstance(result_obj, dict):
            print(f"[run_matching] unexpected type: {type(result_obj)} -> fallback")
            return {"candidates": [], "proposal_draft": ""}
        return result_obj
    except Exception as e:
        print(f"[run_matching] parse error: {e} / raw: {result[:100]}")
        return {"candidates": [], "proposal_draft": ""}


def notion_query(db_id, filter_obj=None):
    results, payload = [], {"page_size": 100}
    if filter_obj:
        payload["filter"] = filter_obj
    while True:
        r = requests.post(f"https://api.notion.com/v1/databases/{db_id}/query",
                         headers=NOTION_HEADERS, json=payload)
        data = r.json()
        results.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data["next_cursor"]
    return results


def register_engineer(info, raw_text, sender):
    name = info.get("name") or "(no name)"
    note = f"[LINE auto-register: {sender}]\n{info.get('note', raw_text[:1500])}"
    props = {
        "\u540d\u524d": {"title": [{"text": {"content": name}}]},
        "\u7a3c\u50cd\u72b6\u6cc1": {"select": {"name": "\u7a3c\u50cd\u53ef\u80fd"}},
        "\u5099\u8003\uff08LINE\u30e1\u30e2\uff09": {"rich_text": [{"text": {"content": note[:2000]}}]}
    }
    skills = [s for s in info.get("skills", []) if s in VALID_SKILLS]
    if skills: props["\u30b9\u30ad\u30eb"] = {"multi_select": [{"name": s} for s in skills]}
    price_val = normalize_price(info.get("price", 0))
    if price_val: props["\u5358\u4fa1\uff08\u4e07\u5186\uff09"] = {"number": price_val}
    if info.get("experience_years"): props["\u7d4c\u9a13\u5e74\u6570"] = {"number": info["experience_years"]}
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
        "\u6848\u4ef6\u540d": {"title": [{"text": {"content": name}}]},
        "\u30b9\u30c6\u30fc\u30bf\u30b9": {"select": {"name": "\u52df\u96c6\u4e2d"}},
        "\u5099\u8003": {"rich_text": [{"text": {"content": note[:2000]}}]}
    }
    req = [s for s in info.get("required_skills", []) if s in VALID_SKILLS]
    opt = [s for s in info.get("optional_skills", []) if s in VALID_SKILLS]
    if req: props["\u5fc5\u8981\u30b9\u30ad\u30eb"] = {"multi_select": [{"name": s} for s in req]}
    if opt: props["\u5c1a\u53ef\u30b9\u30ad\u30eb"] = {"multi_select": [{"name": s} for s in opt]}
    price_val = normalize_price(info.get("price", 0))
    if price_val: props["\u5358\u4fa1\uff08\u4e07\u5186\uff09"] = {"number": price_val}
    if info.get("location"): props["\u52e4\u52d9\u5730"] = {"rich_text": [{"text": {"content": info["location"]}}]}
    res = requests.post("https://api.notion.com/v1/pages", headers=NOTION_HEADERS,
                       json={"parent": {"database_id": NOTION_PROJECT_DB_ID}, "properties": props})
    print(f"register_project status: {res.status_code}")
    if res.status_code == 200:
        return True, res.json()["id"]
    print(res.text[:300])
    return False, ""


def get_available_engineers():
    pages = notion_query(NOTION_ENGINEER_DB_ID, {
        "property": "\u7a3c\u50cd\u72b6\u6cc1",
        "select": {"equals": "\u7a3c\u50cd\u53ef\u80fd"}
    })
    result = []
    for p in pages:
        props = p["properties"]
        name_items = props.get("\u540d\u524d", {}).get("title", [])
        name = name_items[0].get("plain_text", "unknown") if name_items else "unknown"
        skills = [o["name"] for o in props.get("\u30b9\u30ad\u30eb", {}).get("multi_select", [])]
        price = props.get("\u5358\u4fa1\uff08\u4e07\u5186\uff09", {}).get("number", 0) or 0
        note_items = props.get("\u5099\u8003\uff08LINE\u30e1\u30e2\uff09", {}).get("rich_text", [])
        note = note_items[0].get("plain_text", "") if note_items else ""
        source = "unknown"
        if "LINE auto-register: matsuno" in note.lower() or "line auto-register: \u677e\u91ce" in note: source = "matsuno"
        elif "LINE auto-register: okamoto" in note.lower() or "line auto-register: \u5ca1\u672c" in note: source = "okamoto"
        result.append({"name": name, "skills": skills, "price": price, "note": note[:300], "source": source})
    return result


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


def get_user_id_and_token(person):
    if person in ("matsuno", "\u677e\u91ce"): return MATSUNO_USER_ID, MATSUNO_CHANNEL_TOKEN
    if person in ("okamoto", "\u5ca1\u672c"): return OKAMOTO_USER_ID, OKAMOTO_CHANNEL_TOKEN
    return None, None


def process_message(text, reply_token, sender, sender_token):
    print(f"[{sender}] {text[:80]}")
    info = classify_message(text)
    msg_type = info.get("type", "other")
    print(f"[type] {msg_type}")

    if msg_type == "engineer":
        success, _ = register_engineer(info, text, sender)
        name = info.get("name", "(no name)")
        skills_str = ", ".join(info.get("skills", [])) or "N/A"
        price = normalize_price(info.get("price", 0))
        if success:
            reply_message(reply_token,
                f"\u2705 \u767b\u9332\u5b8c\u4e86\n\n\u540d\u524d: {name}\n\u30b9\u30ad\u30eb: {skills_str}\n\u5358\u4fa1: {price}\u4e07\u5186",
                sender_token)
        else:
            reply_message(reply_token, "\u274c \u767b\u9332\u5931\u6557", sender_token)

    elif msg_type == "project":
        success, _ = register_project(info, text, sender)
        proj_name = info.get("name", "project")
        if not success:
            reply_message(reply_token, "\u274c \u6848\u4ef6\u767b\u9332\u5931\u6557", sender_token)
            return
        engineers = get_available_engineers()
        matching = run_matching(info, engineers)
        candidates = matching.get("candidates", [])
        proposal_draft = matching.get("proposal_draft", "")
        if not candidates:
            reply_message(reply_token, f"\u2705 \u6848\u4ef6\u300c{proj_name}\u300d\u767b\u9332\u5b8c\u4e86\n\n\u26a0\ufe0f \u30de\u30c3\u30c1\u5019\u88dc\u8005\u306a\u3057", sender_token)
            return
        msg = f"\u2705 \u6848\u4ef6\u300c{proj_name}\u300d\u767b\u9332\u30fb\u30de\u30c3\u30c1\u30f3\u30b0\u5b8c\u4e86\n\n\u5019\u88dc: {len(candidates)}\u540d\n"
        for i, c in enumerate(candidates[:3], 1):
            msg += f"{i}. {c['name']} / {c.get('price',0)}\u4e07\u5186\n"
        msg += f"\n\u63d0\u6848\u6587:\n{proposal_draft[:1000] if proposal_draft else '(none)'}"
        msg += "\n\n\u78ba\u8a8d\u5f8c\u300c\u9001\u4fe1\u3057\u3066\u300d\u3068\u8fd4\u4fe1\u3057\u3066\u304f\u3060\u3055\u3044"
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
