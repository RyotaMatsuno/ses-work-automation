"""
LINE Webhook サーバー
パートナー企業からのLINEメッセージを受信して
NotionのエンジニアDBに自動登録する
"""

import os
import hmac
import hashlib
import base64
import json
import re
from flask import Flask, request, abort
import requests
from dotenv import dotenv_values

# .envから設定を読み込む
env_path = os.path.join(os.path.dirname(__file__), '..', 'config', '.env')
config = dotenv_values(env_path)

LINE_CHANNEL_SECRET = config['LINE_CHANNEL_SECRET']
LINE_CHANNEL_ACCESS_TOKEN = config['LINE_CHANNEL_ACCESS_TOKEN']
NOTION_API_KEY = config['NOTION_API_KEY']
NOTION_ENGINEER_DB_ID = config['NOTION_ENGINEER_DB_ID']

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

def verify_signature(body: bytes, signature: str) -> bool:
    """LINE署名の検証"""
    hash = hmac.new(LINE_CHANNEL_SECRET.encode('utf-8'), body, hashlib.sha256).digest()
    expected = base64.b64encode(hash).decode('utf-8')
    return hmac.compare_digest(expected, signature)

def parse_engineer_info(text: str) -> dict:
    """
    メッセージテキストからエンジニア情報を抽出する

    対応フォーマット例:
    名前：山田太郎
    スキル：Java, Python, AWS
    単価：70万円
    稼働可能日：2024年4月1日
    経験年数：5年
    連絡先：090-1234-5678
    メール：yamada@example.com
    備考：フルリモート希望
    """
    info = {}

    # 名前
    name_match = re.search(r'名前[：:]\s*(.+)', text)
    if name_match:
        info['name'] = name_match.group(1).strip()

    # スキル
    skill_match = re.search(r'スキル[：:]\s*(.+)', text)
    if skill_match:
        skills_raw = skill_match.group(1).strip()
        info['skills'] = [s.strip() for s in re.split(r'[,、，]', skills_raw)]

    # 単価
    price_match = re.search(r'単価[：:]\s*(\d+)', text)
    if price_match:
        info['price'] = int(price_match.group(1))

    # 稼働可能日
    date_match = re.search(r'稼働可能日[：:]\s*(\d{4}[年/\-]\d{1,2}[月/\-]\d{1,2})', text)
    if date_match:
        date_str = date_match.group(1)
        # "年月日"形式を"YYYY-MM-DD"に変換
        date_str = re.sub(r'(\d{4})年(\d{1,2})月(\d{1,2})日?',
                          lambda m: f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}",
                          date_str)
        info['available_date'] = date_str

    # 経験年数
    exp_match = re.search(r'経験年数[：:]\s*(\d+)', text)
    if exp_match:
        info['experience'] = int(exp_match.group(1))

    # 連絡先
    tel_match = re.search(r'連絡先[：:]\s*([\d\-]+)', text)
    if tel_match:
        info['tel'] = tel_match.group(1).strip()

    # メール
    email_match = re.search(r'メール[：:]\s*(\S+@\S+)', text)
    if email_match:
        info['email'] = email_match.group(1).strip()

    # 備考
    note_match = re.search(r'備考[：:]\s*(.+)', text)
    if note_match:
        info['note'] = note_match.group(1).strip()

    return info

def register_to_notion(engineer_info: dict, raw_message: str) -> bool:
    """NotionのエンジニアDBにエンジニア情報を登録"""

    # エンジニア名がない場合はメッセージ全文を備考に入れる
    if 'name' not in engineer_info:
        engineer_info['name'] = '（名前未記載）'
        engineer_info['note'] = raw_message

    # スキルのmulti_selectオプション
    valid_skills = ["Java", "Python", "PHP", "JavaScript", "TypeScript",
                    "C#", "Node.js", "React", "AWS", "インフラ"]

    properties = {
        "名前": {
            "title": [{"text": {"content": engineer_info.get('name', '未記載')}}]
        },
        "稼働状況": {
            "select": {"name": "稼働可能"}
        },
        "備考（LINEメモ）": {
            "rich_text": [{"text": {"content": engineer_info.get('note', raw_message)[:2000]}}]
        }
    }

    # スキル（有効なスキルのみ）
    if 'skills' in engineer_info:
        matched_skills = [s for s in engineer_info['skills'] if s in valid_skills]
        if matched_skills:
            properties["スキル"] = {
                "multi_select": [{"name": s} for s in matched_skills]
            }

    # 単価
    if 'price' in engineer_info:
        properties["単価（万円）"] = {"number": engineer_info['price']}

    # 稼働可能日
    if 'available_date' in engineer_info:
        properties["稼働可能日"] = {"date": {"start": engineer_info['available_date']}}

    # 経験年数
    if 'experience' in engineer_info:
        properties["経験年数"] = {"number": engineer_info['experience']}

    # 連絡先
    if 'tel' in engineer_info:
        properties["連絡先"] = {"phone_number": engineer_info['tel']}

    # メール
    if 'email' in engineer_info:
        properties["メール"] = {"email": engineer_info['email']}

    data = {
        "parent": {"database_id": NOTION_ENGINEER_DB_ID},
        "properties": properties
    }

    res = requests.post(
        "https://api.notion.com/v1/pages",
        headers=NOTION_HEADERS,
        json=data
    )

    if res.status_code == 200:
        print(f"Notion登録成功: {engineer_info.get('name')}")
        return True
    else:
        print(f"Notion登録エラー: {res.status_code} {res.text}")
        return False

def send_line_reply(reply_token: str, message: str):
    """LINE返信メッセージを送信"""
    data = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": message}]
    }
    requests.post(
        "https://api.line.me/v2/bot/message/reply",
        headers=LINE_HEADERS,
        json=data
    )

@app.route('/webhook', methods=['POST'])
def webhook():
    # 署名検証
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

        print(f"受信メッセージ: {text}")

        # エンジニア情報を解析
        engineer_info = parse_engineer_info(text)

        # Notionに登録
        success = register_to_notion(engineer_info, text)

        if success:
            name = engineer_info.get('name', '要員')
            send_line_reply(reply_token,
                f"✅ {name}さんの情報をNotionに登録しました！\n\nスキル: {', '.join(engineer_info.get('skills', ['未記載']))}\n単価: {engineer_info.get('price', '未記載')}万円")
        else:
            send_line_reply(reply_token,
                "❌ Notionへの登録に失敗しました。管理者に確認してください。")

    return 'OK', 200

@app.route('/health', methods=['GET'])
def health():
    return 'OK', 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Webhook サーバー起動中... port:{port}")
    app.run(host='0.0.0.0', port=port)
