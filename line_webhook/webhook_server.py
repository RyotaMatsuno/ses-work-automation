"""
LINE Webhook サーバー v3
- Claude AIでメッセージを解析（人材 or 案件を自動判定）
- 人材情報 → エンジニアDB登録 → LINE返信
- 案件情報 → 案件DB登録 → マッチングAI → 提案文ドラフト → LINE返信
- ダブルチェックは岡本のClaude Desktopで実施（double_check/double_check.py）
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
from dotenv import dotenv_values

env_path = os.path.join(os.path.dirname(__file__), '..', 'config', '.env')
if os.path.exists(env_path):
    config = dotenv_values(env_path)
    for key, value in config.items():
        if key not in os.environ:
            os.environ[key] = value

LINE_CHANNEL_SECRET       = os.environ.get('LINE_CHANNEL_SECRET', '')
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', '')
NOTION_API_KEY            = os.environ.get('NOTION_API_KEY', '')
NOTION_ENGINEER_DB_ID     = os.environ.get('NOTION_ENGINEER_DB_ID', '')
NOTION_PROJECT_DB_ID      = os.environ.get('NOTION_PROJECT_DB_ID', '')
ANTHROPIC_API_KEY         = os.environ.get('ANTHROPIC_API_KEY', '')

app = Flask(__name__)

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}
LINE_HEADERS = {
    "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
    "Content-Type": "application/json"
}


# ============================================================
# 署名検証
# ============================================================

def verify_signature(body: bytes, signature: str) -> bool:
    h = hmac.new(LINE_CHANNEL_SECRET.encode('utf-8'), body, hashlib.sha256).digest()
    return hmac.compare_digest(base64.b64encode(h).decode('utf-8'), signature)


# ============================================================
# Claude AI呼び出し
# ============================================================

def call_claude(system_prompt: str, user_message: str) -> str:
    res = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },
        json={
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 1500,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}]
        },
        timeout=30
    )
    if res.status_code == 200:
        return res.json()["content"][0]["text"]
    print(f"Claude APIエラー: {res.status_code} {res.text}")
    return ""


def ai_classify_message(text: str) -> dict:
    """メッセージが人材/案件/その他かをAIで判定し構造化データをJSONで返す"""
    system = """あなたはSES業界の情報解析AIです。
受け取ったメッセージを解析して、JSON形式のみで返答してください。説明文は不要です。

人材情報の場合:
{
  "type": "engineer",
  "name": "氏名（不明なら空文字）",
  "skills": ["スキル1", "スキル2"],
  "price": 単価の数値（万円、不明なら0）,
  "available_date": "YYYY-MM-DD形式（不明なら空文字）",
  "experience_years": 経験年数の数値（不明なら0）,
  "company": "所属会社名（不明なら空文字）",
  "note": "備考・その他情報"
}

案件情報の場合:
{
  "type": "project",
  "name": "案件名（不明なら空文字）",
  "required_skills": ["必須スキル1", "必須スキル2"],
  "optional_skills": ["尚可スキル1"],
  "price": 案件単価の数値（万円、不明なら0）,
  "start_date": "YYYY-MM-DD形式（不明なら空文字）",
  "location": "勤務地（不明なら空文字）",
  "remote": "可または不可または一部可または不明",
  "period": "期間",
  "interview_count": 面談回数の数値（不明なら1）,
  "foreign_ok": false,
  "note": "業務内容・その他情報"
}

どちらでもない場合:
{
  "type": "other",
  "note": "内容の要約"
}"""

    result = call_claude(system, text)
    try:
        clean = re.sub(r'```json|```', '', result).strip()
        return json.loads(clean)
    except Exception as e:
        print(f"JSON解析エラー: {e}")
        return {"type": "other", "note": text[:500]}


def ai_matching(project: dict, engineers: list) -> dict:
    """マッチングAI: 候補者選定と提案文ドラフト生成"""
    system = """あなたはSES業界のマッチングAIです。
案件情報とエンジニアリストから候補者を選定して提案文ドラフトをJSONで返してください。

【除外ルール】
- 必須スキルに✕があるエンジニアは除外
- 単価乖離5万円超は除外（案件単価-5万〜+2万の範囲のみ）
- 稼働状況が稼働中は除外

【サマリー文ルール（禁止ワード: 充足・即戦力です）】
- 必須全○+尚可全○ → "必須・尚可ともにマッチ度高い人員"
- 必須全○+尚可○率50%以上 → "必須全て満たしており、尚可も○項目経験あり"
- 必須全○のみ → "必須スキル全て満たし即稼働可能"

返答するJSONフォーマット:
{
  "candidates": [
    {
      "name": "氏名",
      "price": 提案単価（数値）,
      "summary": "サマリー文",
      "required_match": {"スキル名": true/false},
      "optional_match": {"スキル名": true/false},
      "parallel": "並行状況テキスト"
    }
  ],
  "proposal_draft": "案件担当者向け提案メール本文"
}"""

    payload = {"project": project, "engineers": engineers}
    result = call_claude(system, json.dumps(payload, ensure_ascii=False))
    try:
        clean = re.sub(r'```json|```', '', result).strip()
        return json.loads(clean)
    except Exception as e:
        print(f"マッチングAI JSONエラー: {e}")
        return {"candidates": [], "proposal_draft": ""}


# ============================================================
# Notion操作
# ============================================================

def notion_query(db_id: str, filter_obj: dict = None) -> list:
    results = []
    payload = {"page_size": 100}
    if filter_obj:
        payload["filter"] = filter_obj
    while True:
        r = requests.post(
            f"https://api.notion.com/v1/databases/{db_id}/query",
            headers=NOTION_HEADERS, json=payload
        )
        data = r.json()
        results.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data["next_cursor"]
    return results


VALID_SKILLS = [
    "Java", "Python", "PHP", "JavaScript", "TypeScript", "C#", "Node.js",
    "React", "AWS", "インフラ", "Go", "Ruby", "Swift", "Kotlin", "Vue.js",
    "Angular", "Docker", "Kubernetes", "GCP", "Azure", "Spring",
    "MySQL", "PostgreSQL", "Oracle", "MongoDB", "Linux"
]


def register_engineer(info: dict, raw_text: str) -> tuple[bool, str]:
    name = info.get("name") or "（名前未記載）"
    note = f"【LINEから自動登録】\n{info.get('note', raw_text[:1500])}"
    properties = {
        "名前": {"title": [{"text": {"content": name}}]},
        "稼働状況": {"select": {"name": "稼働可能"}},
        "備考（LINEメモ）": {"rich_text": [{"text": {"content": note[:2000]}}]}
    }
    skills = [s for s in info.get("skills", []) if s in VALID_SKILLS]
    if skills:
        properties["スキル"] = {"multi_select": [{"name": s} for s in skills]}
    if info.get("price"):
        properties["単価（万円）"] = {"number": info["price"]}
    if info.get("available_date"):
        properties["稼働可能日"] = {"date": {"start": info["available_date"]}}
    if info.get("experience_years"):
        properties["経験年数"] = {"number": info["experience_years"]}
    res = requests.post(
        "https://api.notion.com/v1/pages",
        headers=NOTION_HEADERS,
        json={"parent": {"database_id": NOTION_ENGINEER_DB_ID}, "properties": properties}
    )
    if res.status_code == 200:
        return True, res.json()["id"]
    print(f"エンジニア登録エラー: {res.status_code} {res.text}")
    return False, ""


def register_project(info: dict, raw_text: str) -> tuple[bool, str]:
    name = info.get("name") or "（案件名未記載）"
    note = f"【LINEから自動登録】\n{info.get('note', raw_text[:1500])}"
    properties = {
        "案件名": {"title": [{"text": {"content": name}}]},
        "ステータス": {"select": {"name": "募集中"}},
        "備考": {"rich_text": [{"text": {"content": note[:2000]}}]}
    }
    req = [s for s in info.get("required_skills", []) if s in VALID_SKILLS]
    opt = [s for s in info.get("optional_skills", []) if s in VALID_SKILLS]
    if req:
        properties["必要スキル"] = {"multi_select": [{"name": s} for s in req]}
    if opt:
        properties["尚可スキル"] = {"multi_select": [{"name": s} for s in opt]}
    if info.get("price"):
        properties["単価（万円）"] = {"number": info["price"]}
    if info.get("start_date"):
        properties["開始日"] = {"date": {"start": info["start_date"]}}
    if info.get("location"):
        properties["勤務地"] = {"rich_text": [{"text": {"content": info["location"]}}]}
    res = requests.post(
        "https://api.notion.com/v1/pages",
        headers=NOTION_HEADERS,
        json={"parent": {"database_id": NOTION_PROJECT_DB_ID}, "properties": properties}
    )
    if res.status_code == 200:
        return True, res.json()["id"]
    print(f"案件登録エラー: {res.status_code} {res.text}")
    return False, ""


def get_available_engineers() -> list:
    pages = notion_query(NOTION_ENGINEER_DB_ID, {
        "property": "稼働状況",
        "select": {"equals": "稼働可能"}
    })
    engineers = []
    for p in pages:
        props = p["properties"]
        name_prop = props.get("名前", {}).get("title", [])
        name = name_prop[0]["plain_text"] if name_prop else "未記載"
        skills = [o["name"] for o in props.get("スキル", {}).get("multi_select", [])]
        price = props.get("単価（万円）", {}).get("number", 0) or 0
        avail = props.get("稼働可能日", {}).get("date") or {}
        note_prop = props.get("備考（LINEメモ）", {}).get("rich_text", [])
        note = note_prop[0]["plain_text"] if note_prop else ""
        engineers.append({
            "name": name,
            "skills": skills,
            "price": price,
            "available_date": avail.get("start", ""),
            "note": note[:300],
            "notion_id": p["id"]
        })
    return engineers


# ============================================================
# LINE返信
# ============================================================

def send_line_reply(reply_token: str, message: str):
    if len(message) > 4900:
        message = message[:4900] + "\n…（省略）"
    requests.post(
        "https://api.line.me/v2/bot/message/reply",
        headers=LINE_HEADERS,
        json={"replyToken": reply_token, "messages": [{"type": "text", "text": message}]}
    )


# ============================================================
# メイン処理フロー
# ============================================================

def process_message(text: str, reply_token: str):
    print(f"[処理開始] {text[:80]}")

    # STEP1: AI判定
    info = ai_classify_message(text)
    msg_type = info.get("type", "other")
    print(f"[判定] type={msg_type}")

    # STEP2: 人材情報 → エンジニアDB登録
    if msg_type == "engineer":
        success, _ = register_engineer(info, text)
        if not success:
            send_line_reply(reply_token, "❌ エンジニア情報のNotion登録に失敗しました。")
            return
        name = info.get("name", "（名前未記載）")
        skills_str = "、".join(info.get("skills", [])) or "未記載"
        price = info.get("price", 0)
        send_line_reply(
            reply_token,
            f"✅ エンジニア情報をNotionに登録しました\n\n"
            f"👤 {name}\n"
            f"💻 スキル: {skills_str}\n"
            f"💴 単価: {price}万円"
        )
        return

    # STEP3: 案件情報 → 案件DB登録 → マッチング → 提案文ドラフト返信
    elif msg_type == "project":
        success, _ = register_project(info, text)
        if not success:
            send_line_reply(reply_token, "❌ 案件情報のNotion登録に失敗しました。")
            return

        engineers = get_available_engineers()
        matching_result = ai_matching(info, engineers)
        candidates = matching_result.get("candidates", [])
        proposal_draft = matching_result.get("proposal_draft", "")

        proj_name = info.get("name", "案件")

        if not candidates:
            send_line_reply(
                reply_token,
                f"✅ 案件「{proj_name}」をNotionに登録しました\n\n"
                f"⚠️ マッチする候補者が見つかりませんでした。\n"
                f"エンジニアDBを確認してください。"
            )
            return

        # 返信: 候補者リスト + 提案文ドラフト
        # ※ダブルチェックは岡本のClaudeで実施
        reply = f"✅ 案件「{proj_name}」登録 + マッチング完了\n\n"
        reply += f"【候補者: {len(candidates)}名】\n"
        for i, c in enumerate(candidates[:3], 1):
            mark = "①②③"[i-1]
            reply += f"{mark} {c['name']} / {c.get('price',0)}万円\n"
            reply += f"   {c.get('summary','')}\n"

        reply += f"\n【提案文ドラフト】\n"
        reply += proposal_draft[:1500] if proposal_draft else "（生成できませんでした）"
        reply += "\n\n⚠️ 送信前に岡本のClaudeでダブルチェックを実施してください"

        send_line_reply(reply_token, reply)

    else:
        send_line_reply(
            reply_token,
            "メッセージを受信しました。\n\n"
            "人材情報または案件情報を送ってください。\n"
            "自由なフォーマットで送信可能です。"
        )


# ============================================================
# Flask エンドポイント
# ============================================================

@app.route('/webhook', methods=['POST'])
def webhook():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data()
    if not verify_signature(body, signature):
        abort(400)
    events = request.json.get('events', [])
    for event in events:
        if event['type'] != 'message':
            continue
        if event['message']['type'] != 'text':
            continue
        text = event['message']['text']
        reply_token = event['replyToken']
        try:
            process_message(text, reply_token)
        except Exception as e:
            print(f"処理エラー: {e}")
            send_line_reply(reply_token, f"❌ エラーが発生しました: {str(e)[:100]}")
    return 'OK', 200


@app.route('/health', methods=['GET'])
def health():
    return 'OK', 200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Webhook サーバー起動中... port:{port}")
    app.run(host='0.0.0.0', port=port)
