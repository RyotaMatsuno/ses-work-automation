"""
LINE Webhook サーバー v6
- 松野/岡本どちらの公式LINEからでも受信
- 送信者（松野/岡本）をuserIdで判定
- 案件×人材の4パターン担当振り分け
- 松野・岡本それぞれの個人LINEにpush送信
- 元メッセージへのリプライ形式
"""

import os
import hmac
import hashlib
import base64
import json
import re
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

# 松野アカウント
MATSUNO_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET', '')
MATSUNO_CHANNEL_TOKEN  = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', '')
MATSUNO_USER_ID        = os.environ.get('MATSUNO_LINE_USER_ID', '')

# 岡本アカウント
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
    "Java", "Python", "PHP", "JavaScript", "TypeScript", "C#", "Node.js",
    "React", "AWS", "インフラ", "Go", "Ruby", "Swift", "Kotlin", "Vue.js",
    "Angular", "Docker", "Kubernetes", "GCP", "Azure", "Spring",
    "MySQL", "PostgreSQL", "Oracle", "MongoDB", "Linux", "Salesforce",
    "SAP", "Tableau", "PowerBI", "Terraform", "Jenkins", "GitLab"
]

DOUBLE_CHECK_SYSTEM = f"""あなたはSES業界のダブルチェック専門AIです。
今日の日付: {date.today().isoformat()}

【チェック項目】
1. 除外ルール: 外国籍/地方在住/短期連続/ブランク/既往歴
2. 単価・粗利: 粗利5万円未満NG（目標7万）
3. 並行スコア: 合計5.0以上NG
4. 敬語: 「充足」「即戦力です」「教えてください」NG
5. マスキング: 企業名・担当者名・連絡先の漏れ

【出力フォーマット】
【判定】OK / NG
【チェック結果】各項目OK/NG
【修正済み提案文】NGなら修正版、OKなら「修正不要」
【所見】気になる点"""


# ============================================================
# 署名検証
# ============================================================

def verify_signature(body: bytes, signature: str, secret: str) -> bool:
    h = hmac.new(secret.encode('utf-8'), body, hashlib.sha256).digest()
    return hmac.compare_digest(base64.b64encode(h).decode('utf-8'), signature)


# ============================================================
# Claude AI呼び出し
# ============================================================

def call_claude(system: str, user_msg: str, max_tokens: int = 2000) -> str:
    res = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },
        json={
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user_msg}]
        },
        timeout=60
    )
    if res.status_code == 200:
        return res.json()["content"][0]["text"]
    print(f"Claude APIエラー: {res.status_code}")
    return ""


def classify_message(text: str) -> dict:
    system = """SES業界の情報解析AI。JSONのみ返答。

人材の場合:
{"type":"engineer","name":"氏名","skills":[],"price":0,"available_date":"","experience_years":0,"note":""}

案件の場合:
{"type":"project","name":"案件名","required_skills":[],"optional_skills":[],"price":0,"start_date":"","location":"","remote":"不明","period":"","note":""}

どちらでもない場合:
{"type":"other","note":""}"""
    result = call_claude(system, text, max_tokens=800)
    try:
        return json.loads(re.sub(r'```json|```', '', result).strip())
    except:
        return {"type": "other", "note": text[:300]}


def run_matching(project: dict, engineers: list) -> dict:
    system = """SES業界マッチングAI。JSONのみ返答。
除外: 必須スキル欠如 / 単価乖離5万超 / 稼働中
サマリー禁止ワード: 充足・即戦力です

{"candidates":[{"name":"","price":0,"summary":"","required_match":{},"optional_match":{},"parallel":"なし","engineer_source":"松野 or 岡本 or 不明"}],"proposal_draft":""}"""
    result = call_claude(system, json.dumps({"project": project, "engineers": engineers}, ensure_ascii=False), max_tokens=2000)
    try:
        return json.loads(re.sub(r'```json|```', '', result).strip())
    except:
        return {"candidates": [], "proposal_draft": ""}


def run_double_check(proj_name: str, proposal: str, candidates: list) -> tuple:
    check_input = f"【案件名】{proj_name}\n\n【提案文】\n{proposal}\n\n【候補者】\n"
    for c in candidates:
        check_input += f"- {c['name']} / {c.get('price',0)}万円 / 並行:{c.get('parallel','なし')}\n"
    result = call_claude(DOUBLE_CHECK_SYSTEM, check_input, max_tokens=2000)
    is_ok = "【判定】OK" in result
    final = proposal
    if "【修正済み提案文】" in result:
        after = result.split("【修正済み提案文】", 1)[1].strip()
        if "【所見】" in after:
            after = after.split("【所見】")[0].strip()
        if after and after != "修正不要":
            final = after
    return is_ok, result, final


# ============================================================
# Notion操作
# ============================================================

def notion_query(db_id: str, filter_obj: dict = None) -> list:
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


def register_engineer(info: dict, raw_text: str, sender: str) -> tuple:
    name = info.get("name") or "（名前未記載）"
    note = f"【LINEから自動登録: {sender}】\n{info.get('note', raw_text[:1500])}"
    props = {
        "名前": {"title": [{"text": {"content": name}}]},
        "稼働状況": {"select": {"name": "稼働可能"}},
        "備考（LINEメモ）": {"rich_text": [{"text": {"content": note[:2000]}}]}
    }
    skills = [s for s in info.get("skills", []) if s in VALID_SKILLS]
    if skills: props["スキル"] = {"multi_select": [{"name": s} for s in skills]}
    if info.get("price"): props["単価（万円）"] = {"number": info["price"]}
    if info.get("available_date"): props["稼働可能日"] = {"date": {"start": info["available_date"]}}
    if info.get("experience_years"): props["経験年数"] = {"number": info["experience_years"]}
    res = requests.post("https://api.notion.com/v1/pages", headers=NOTION_HEADERS,
                       json={"parent": {"database_id": NOTION_ENGINEER_DB_ID}, "properties": props})
    if res.status_code == 200:
        return True, res.json()["id"]
    return False, ""


def register_project(info: dict, raw_text: str, sender: str) -> tuple:
    name = info.get("name") or "（案件名未記載）"
    note = f"【LINEから自動登録: {sender}】\n{info.get('note', raw_text[:1500])}"
    props = {
        "案件名": {"title": [{"text": {"content": name}}]},
        "ステータス": {"select": {"name": "募集中"}},
        "備考": {"rich_text": [{"text": {"content": note[:2000]}}]}
    }
    req = [s for s in info.get("required_skills", []) if s in VALID_SKILLS]
    opt = [s for s in info.get("optional_skills", []) if s in VALID_SKILLS]
    if req: props["必要スキル"] = {"multi_select": [{"name": s} for s in req]}
    if opt: props["尚可スキル"] = {"multi_select": [{"name": s} for s in opt]}
    if info.get("price"): props["単価（万円）"] = {"number": info["price"]}
    if info.get("start_date"): props["開始日"] = {"date": {"start": info["start_date"]}}
    if info.get("location"): props["勤務地"] = {"rich_text": [{"text": {"content": info["location"]}}]}
    res = requests.post("https://api.notion.com/v1/pages", headers=NOTION_HEADERS,
                       json={"parent": {"database_id": NOTION_PROJECT_DB_ID}, "properties": props})
    if res.status_code == 200:
        return True, res.json()["id"]
    return False, ""


def get_available_engineers() -> list:
    pages = notion_query(NOTION_ENGINEER_DB_ID, {"property": "稼働状況", "select": {"equals": "稼働可能"}})
    result = []
    for p in pages:
        props = p["properties"]
        name_prop = props.get("名前", {}).get("title", [])
        name = name_prop[0]["plain_text"] if name_prop else "未記載"
        skills = [o["name"] for o in props.get("スキル", {}).get("multi_select", [])]
        price = props.get("単価（万円）", {}).get("number", 0) or 0
        note_prop = props.get("備考（LINEメモ）", {}).get("rich_text", [])
        note = note_prop[0]["plain_text"] if note_prop else ""
        source = "不明"
        if "LINEから自動登録: 松野" in note: source = "松野"
        elif "LINEから自動登録: 岡本" in note: source = "岡本"
        result.append({"name": name, "skills": skills, "price": price,
                       "note": note[:300], "notion_id": p["id"], "source": source})
    return result


# ============================================================
# LINE送信
# ============================================================

def reply_message(reply_token: str, text: str, token: str):
    if len(text) > 4900: text = text[:4900] + "\n…（省略）"
    requests.post(
        "https://api.line.me/v2/bot/message/reply",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"replyToken": reply_token, "messages": [{"type": "text", "text": text}]}
    )


def push_message(user_id: str, text: str, token: str):
    if not user_id: return
    if len(text) > 4900: text = text[:4900] + "\n…（省略）"
    requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"to": user_id, "messages": [{"type": "text", "text": text}]}
    )


# ============================================================
# 担当振り分け
# ============================================================

def determine_roles(project_sender: str, engineer_source: str) -> dict:
    if project_sender == "松野" and engineer_source == "松野":
        return {"proposal_owner": "松野", "intent_owner": "松野"}
    elif project_sender == "岡本" and engineer_source == "岡本":
        return {"proposal_owner": "岡本", "intent_owner": "岡本"}
    elif project_sender == "岡本" and engineer_source == "松野":
        return {"proposal_owner": "岡本", "intent_owner": "松野"}
    elif project_sender == "松野" and engineer_source == "岡本":
        return {"proposal_owner": "松野", "intent_owner": "岡本"}
    else:
        return {"proposal_owner": "両方", "intent_owner": "両方"}


def get_user_id_and_token(person: str) -> tuple:
    if person == "松野":
        return MATSUNO_USER_ID, MATSUNO_CHANNEL_TOKEN
    elif person == "岡本":
        return OKAMOTO_USER_ID, OKAMOTO_CHANNEL_TOKEN
    return None, None


# ============================================================
# メイン処理
# ============================================================

def process_message(text: str, reply_token: str, sender: str, sender_token: str):
    print(f"[{sender}] {text[:80]}")

    info = classify_message(text)
    msg_type = info.get("type", "other")
    print(f"[判定] {msg_type}")

    if msg_type == "engineer":
        success, _ = register_engineer(info, text, sender)
        name = info.get("name", "（名前未記載）")
        skills_str = "、".join(info.get("skills", [])) or "未記載"
        price = info.get("price", 0)
        if success:
            reply_message(reply_token,
                f"✅ 人材情報を登録しました\n\n"
                f"👤 {name}\n💻 スキル: {skills_str}\n💴 単価: {price}万円\n\n"
                f"案件が来たらこの方の情報でマッチングします",
                sender_token)
        else:
            reply_message(reply_token, "❌ 人材情報の登録に失敗しました", sender_token)
        return

    elif msg_type == "project":
        success, _ = register_project(info, text, sender)
        proj_name = info.get("name", "案件")
        if not success:
            reply_message(reply_token, "❌ 案件情報の登録に失敗しました", sender_token)
            return

        engineers = get_available_engineers()
        matching = run_matching(info, engineers)
        candidates = matching.get("candidates", [])
        proposal_draft = matching.get("proposal_draft", "")

        if not candidates:
            reply_message(reply_token,
                f"✅ 案件「{proj_name}」を登録しました\n\n"
                f"⚠️ マッチする候補者が見つかりませんでした\nエンジニアDBを確認してください",
                sender_token)
            return

        is_ok, check_result, final_proposal = run_double_check(proj_name, proposal_draft, candidates)
        print(f"[ダブルチェック] OK={is_ok}")

        sources = [c.get("engineer_source", "不明") for c in candidates]
        main_source = max(set(sources), key=sources.count)
        roles = determine_roles(sender, main_source)
        proposal_owner = roles["proposal_owner"]
        intent_owner = roles["intent_owner"]

        proposal_msg = (
            f"✅ 案件「{proj_name}」登録・マッチング・ダブルチェック完了\n\n"
            f"【候補者: {len(candidates)}名】\n"
        )
        for i, c in enumerate(candidates[:3], 1):
            mark = "①②③"[i-1]
            proposal_msg += f"{mark} {c['name']} / {c.get('price',0)}万円\n"
            proposal_msg += f"   {c.get('summary','')[:60]}\n"
            proposal_msg += f"   並行: {c.get('parallel','なし')}\n"

        proposal_msg += f"\n【ダブルチェック】{'✅ OK' if is_ok else '❌ NG'}\n"
        if not is_ok:
            for line in check_result.split('\n'):
                if 'NG' in line and any(k in line for k in ['除外','単価','並行','敬語','マスキング']):
                    proposal_msg += f"  • {line.strip()}\n"

        proposal_msg += f"\n【提案文（送信可能版）】\n"
        proposal_msg += final_proposal[:1500] if final_proposal else "（生成できませんでした）"
        if intent_owner != sender:
            proposal_msg += f"\n\n※ 意向確認は{intent_owner}が実施中です"
        proposal_msg += "\n\n確認後「送信して」と返信してください"

        reply_message(reply_token, proposal_msg, sender_token)

        if intent_owner != sender and intent_owner != "両方":
            intent_user_id, intent_token = get_user_id_and_token(intent_owner)
            intent_msg = (
                f"📋 意向確認の依頼が来ました\n\n【案件】{proj_name}\n"
                f"必須: {', '.join(info.get('required_skills',[])[:4])}\n"
                f"単価: {info.get('price',0)}万円 / {info.get('location','不明')} / リモート{info.get('remote','不明')}\n\n"
                f"【確認してほしい人材】\n"
            )
            for i, c in enumerate(candidates[:3], 1):
                mark = "①②③"[i-1]
                intent_msg += f"{mark} {c['name']} - {c.get('price',0)}万円\n   {c.get('summary','')[:60]}\n"
            intent_msg += f"\n意向確認後、結果をジョブズに送ってください"
            push_message(intent_user_id, intent_msg, intent_token)

        elif intent_owner == "両方":
            for person in ["松野", "岡本"]:
                if person != sender:
                    uid, tok = get_user_id_and_token(person)
                    push_message(uid,
                        f"📋 {sender}から案件「{proj_name}」が来ました\n担当候補者の確認をお願いします", tok)

    else:
        reply_message(reply_token,
            "メッセージを受信しました。\n\n人材情報または案件情報をテキストで送ってください。\n（自由なフォーマットで大丈夫です）",
            sender_token)


# ============================================================
# Flask エンドポイント
# ============================================================

def handle_webhook(channel_secret: str, channel_token: str, sender_name: str):
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
        if sender_name == "松野" and user_id and not MATSUNO_USER_ID:
            MATSUNO_USER_ID = user_id
            if os.path.exists(ENV_PATH):
                set_key(ENV_PATH, "MATSUNO_LINE_USER_ID", user_id)
            print(f"松野userID自動取得・保存: {user_id}")

        try:
            process_message(event['message']['text'], event['replyToken'], sender_name, channel_token)
        except Exception as e:
            print(f"処理エラー[{sender_name}]: {e}")
    return 'OK', 200


@app.route('/webhook', methods=['POST'])
def webhook_matsuno():
    return handle_webhook(MATSUNO_CHANNEL_SECRET, MATSUNO_CHANNEL_TOKEN, "松野")


@app.route('/webhook_okamoto', methods=['POST'])
def webhook_okamoto():
    return handle_webhook(OKAMOTO_CHANNEL_SECRET, OKAMOTO_CHANNEL_TOKEN, "岡本")


@app.route('/health', methods=['GET'])
def health():
    return 'OK', 200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Webhook v6 起動中... port:{port}")
    app.run(host='0.0.0.0', port=port)
