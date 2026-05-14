"""
LINE Webhook Server v8
- NGになった候補も○×形式で「参考」として提示
- 「送信して」→ OK候補のみ / 「△も含めて送信して」→ 全員送信
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

SHEET_URL_PATTERN = re.compile(r'https://docs\.google\.com/spreadsheets/[^\s]+')

# 案件ごとのマッチング結果を一時保存（Railwayは揮発性のためセッション内のみ有効）
# key: sender+"_latest" → {"ok": [...], "ng": [...], "proposal_draft": ""}
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

If the message contains MULTIPLE engineers (e.g. @All with several people listed):
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
    system = '''Classify this spreadsheet content as engineer profiles or job postings. Reply JSON only.
If it contains engineer/person profiles: {"content_type": "engineer"}
If it contains job postings/projects: {"content_type": "project"}
If unclear: {"content_type": "engineer"}'''
    result = call_claude(system, text[:2000], max_tokens=100)
    try:
        result_obj = json.loads(re.sub(r'```json|```', '', result).strip())
        return result_obj.get("content_type", "engineer")
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
    system = '''SES matching AI. Reply JSON only.
Return ALL engineers as candidates, including partial matches.
For each candidate, evaluate required_skills and optional_skills as match objects with skill name -> true/false.
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


def evaluate_candidate(candidate, project_price):
    """
    候補者をOK/NGに分類し、NG理由を付与する。

    Returns:
        (is_ok: bool, ng_reasons: list[str], detail_str: str)
    """
    ng_reasons = []
    cp = normalize_price(candidate.get("price", 0)) or 0
    pp = project_price or 0

    # 粗利チェック
    if cp == 0:
        ng_reasons.append("単価不明")
    elif pp > 0:
        diff = pp - cp
        if diff < 5:
            ng_reasons.append(f"粗利{diff}万（基準5万未満）")

    # 必須スキルチェック
    required_match = candidate.get("required_match", {})
    missing = [k for k, v in required_match.items() if not v]
    if missing:
        ng_reasons.append(f"必須×: {', '.join(missing)}")

    is_ok = len(ng_reasons) == 0

    # ○×サマリー文字列生成
    req_str = ""
    if required_match:
        req_str = " ".join(f"{'○' if v else '×'}{k}" for k, v in required_match.items())
    opt_match = candidate.get("optional_match", {})
    opt_str = ""
    if opt_match:
        opt_str = " ".join(f"{'○' if v else '△'}{k}" for k, v in opt_match.items())

    detail_parts = []
    if req_str:
        detail_parts.append(f"必須: {req_str}")
    if opt_str:
        detail_parts.append(f"尚可: {opt_str}")
    detail_str = " / ".join(detail_parts)

    return is_ok, ng_reasons, detail_str


def build_matching_message(proj_name, ok_candidates, ng_candidates, proposal_draft):
    """LINEに送るマッチング結果メッセージを組み立てる"""
    msg = f"✅ 案件「{proj_name}」登録・マッチング完了\n\n"

    if ok_candidates:
        msg += f"【✅ OK候補 {len(ok_candidates)}名】\n"
        for i, (c, detail) in enumerate(ok_candidates, 1):
            price = normalize_price(c.get("price", 0)) or 0
            msg += f"{i}. {c['name']} / {price}万円\n"
            if detail:
                msg += f"   {detail}\n"
    else:
        msg += "【✅ OK候補】なし\n"

    if ng_candidates:
        msg += f"\n【△ 参考候補 {len(ng_candidates)}名】\n"
        for i, (c, ng_reasons, detail) in enumerate(ng_candidates, 1):
            price = normalize_price(c.get("price", 0)) or 0
            reason_str = " / ".join(ng_reasons)
            msg += f"{i}. {c['name']} / {price}万円\n"
            msg += f"   ⚠️ {reason_str}\n"
            if detail:
                msg += f"   {detail}\n"

    if proposal_draft:
        msg += f"\n提案文:\n{proposal_draft[:800]}"

    msg += "\n\n"
    if ok_candidates and ng_candidates:
        msg += "「送信して」→ OK候補のみ\n「△も含めて送信して」→ 全員"
    elif ok_candidates:
        msg += "「送信して」で提案します"
    else:
        msg += "「△も含めて送信して」で参考候補を送れます"

    return msg


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
    if req: props["必須スキル"] = {"multi_select": [{"name": s} for s in req]}
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
        "property": "稼働状況",
        "select": {"equals": "稼働可能"}
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
        success_count = 0
        skip_count = 0
        for proj in projects:
            ok, _ = register_project(proj, raw_text, sender)
            if ok: success_count += 1
            else: skip_count += 1
        msg = f"✅ スプレッドシートから案件登録完了\n\n登録: {success_count}件 / スキップ: {skip_count}件\n"
        for i, p in enumerate(projects[:5], 1):
            msg += f"{i}. {p.get('name','(no name)')} / {p.get('price',0)}万円\n"
        if len(projects) > 5:
            msg += f"...他{len(projects)-5}件"
        reply_message(reply_token, msg, sender_token)
    else:
        engineers = extract_engineers_from_text(text)
        if not engineers:
            reply_message(reply_token, "⚠️ 人員情報が抽出できませんでした", sender_token)
            return
        success_count = 0
        skip_count = 0
        for eng in engineers:
            ok, _ = register_engineer(eng, raw_text, sender)
            if ok: success_count += 1
            else: skip_count += 1
        msg = f"✅ スプレッドシートから人員登録完了\n\n登録: {success_count}名 / スキップ: {skip_count}名\n"
        for i, e in enumerate(engineers[:5], 1):
            msg += f"{i}. {e.get('name','(no name)')} / {e.get('price',0)}万円\n"
        if len(engineers) > 5:
            msg += f"...他{len(engineers)-5}名"
        reply_message(reply_token, msg, sender_token)


def process_message(text, reply_token, sender, sender_token):
    print(f"[{sender}] {text[:80]}")

    # ── 送信指示の処理 ──────────────────────────────
    pending_key = sender + "_latest"
    text_stripped = text.strip()

    if text_stripped in ("送信して", "送信"):
        pending = PENDING_PROPOSALS.get(pending_key)
        if not pending:
            reply_message(reply_token, "⚠️ 送信待ちの提案がありません", sender_token)
            return
        draft = pending.get("proposal_draft", "")
        reply_message(reply_token, f"📨 送信しました（OK候補のみ）\n\n{draft[:800]}", sender_token)
        del PENDING_PROPOSALS[pending_key]
        return

    if "△も含めて送信" in text_stripped or "△含めて送信" in text_stripped:
        pending = PENDING_PROPOSALS.get(pending_key)
        if not pending:
            reply_message(reply_token, "⚠️ 送信待ちの提案がありません", sender_token)
            return
        ok_list = pending.get("ok", [])
        ng_list = pending.get("ng", [])
        all_names = [c["name"] for c, *_ in ok_list] + [c["name"] for c, *_ in ng_list]
        draft = pending.get("proposal_draft", "")
        reply_message(reply_token,
            f"📨 送信しました（全{len(all_names)}名）\n参考候補含む\n\n{draft[:800]}",
            sender_token)
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

    if msg_type == "engineer":
        success, _ = register_engineer(info, text, sender)
        name = info.get("name", "(no name)")
        skills_str = ", ".join(info.get("skills", [])) or "N/A"
        price = normalize_price(info.get("price", 0))
        if success:
            reply_message(reply_token,
                f"✅ 登録完了\n\n名前: {name}\nスキル: {skills_str}\n単価: {price}万円",
                sender_token)
        else:
            reply_message(reply_token, "❌ 登録失敗", sender_token)

    elif msg_type == "engineers":
        engineers_list = info.get("engineers", [])
        if not engineers_list:
            reply_message(reply_token, "❌ 人員情報が取得できませんでした", sender_token)
            return
        success_count = 0
        skip_count = 0
        for eng in engineers_list:
            ok, _ = register_engineer(eng, text, sender)
            if ok: success_count += 1
            else: skip_count += 1
        msg = f"✅ 複数人員登録完了\n\n登録: {success_count}名 / スキップ: {skip_count}名\n"
        for i, e in enumerate(engineers_list[:5], 1):
            msg += f"{i}. {e.get('name','(no name)')} / {e.get('price',0)}万円\n"
        reply_message(reply_token, msg, sender_token)

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

        ok_candidates = []   # [(candidate, detail_str), ...]
        ng_candidates = []   # [(candidate, ng_reasons, detail_str), ...]

        for c in all_candidates:
            is_ok, ng_reasons, detail_str = evaluate_candidate(c, project_price)
            if is_ok:
                ok_candidates.append((c, detail_str))
            else:
                ng_candidates.append((c, ng_reasons, detail_str))

        # 保存（送信指示待ち）
        PENDING_PROPOSALS[pending_key] = {
            "ok": ok_candidates,
            "ng": ng_candidates,
            "proposal_draft": proposal_draft,
        }

        msg = build_matching_message(proj_name, ok_candidates, ng_candidates, proposal_draft)
        reply_message(reply_token, msg, sender_token)

    elif msg_type == "projects":
        projects_list = info.get("projects", [])
        if not projects_list:
            reply_message(reply_token, "❌ 案件情報が取得できませんでした", sender_token)
            return
        success_count = 0
        skip_count = 0
        for proj in projects_list:
            ok, _ = register_project(proj, text, sender)
            if ok: success_count += 1
            else: skip_count += 1
        msg = f"✅ 複数案件登録完了\n\n登録: {success_count}件 / スキップ: {skip_count}件\n"
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
