"""
sessalesメールから過去3週間の人材情報を取得してNotionに登録するスクリプト
"""
import imaplib
import email
import re
import json
import requests
from datetime import datetime, timedelta
from email.header import decode_header
from dotenv import dotenv_values
import os

# .env読み込み
env_path = os.path.join(os.path.dirname(__file__), 'config', '.env')
config = dotenv_values(env_path)

IMAP_SERVER = config.get('OUTLOOK_IMAP_SERVER', 'mail65.onamae.ne.jp')
IMAP_PORT = int(config.get('OUTLOOK_IMAP_PORT', 993))
EMAIL_USER = config.get('OUTLOOK_EMAIL', 'sessales@terra-ltd.co.jp')
EMAIL_PASS = config.get('OUTLOOK_PASSWORD', '')
NOTION_API_KEY = config.get('NOTION_API_KEY', '')
NOTION_ENGINEER_DB_ID = config.get('NOTION_ENGINEER_DB_ID', '343450ff-37c0-819d-8769-fb0a8a4ceeb1')

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

VALID_SKILLS = ["Java", "Python", "PHP", "JavaScript", "TypeScript",
                "C#", "Node.js", "React", "AWS", "インフラ"]

def decode_str(s):
    """メールヘッダーのデコード"""
    if s is None:
        return ""
    decoded_parts = decode_header(s)
    result = ""
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            try:
                result += part.decode(charset or 'utf-8', errors='replace')
            except:
                result += part.decode('utf-8', errors='replace')
        else:
            result += str(part)
    return result

def get_email_body(msg):
    """メール本文を取得"""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                charset = part.get_content_charset() or 'utf-8'
                try:
                    body = part.get_payload(decode=True).decode(charset, errors='replace')
                    break
                except:
                    pass
            elif content_type == "text/html" and not body:
                charset = part.get_content_charset() or 'utf-8'
                try:
                    html = part.get_payload(decode=True).decode(charset, errors='replace')
                    # 簡易的なHTMLタグ除去
                    body = re.sub(r'<[^>]+>', ' ', html)
                    body = re.sub(r'&nbsp;', ' ', body)
                    body = re.sub(r'&lt;', '<', body)
                    body = re.sub(r'&gt;', '>', body)
                    body = re.sub(r'&amp;', '&', body)
                except:
                    pass
    else:
        charset = msg.get_content_charset() or 'utf-8'
        try:
            body = msg.get_payload(decode=True).decode(charset, errors='replace')
        except:
            body = str(msg.get_payload())
    return body.strip()

def parse_engineer_from_email(subject, body, sender, date_str):
    """メールから人材情報を抽出"""
    text = f"{subject}\n{body}"
    info = {
        'raw_subject': subject,
        'raw_sender': sender,
        'raw_date': date_str,
        'raw_body': body[:500]  # 最初の500文字
    }

    # 名前の抽出（様々なパターン）
    name_patterns = [
        r'氏名[：:\s]*([^\s\n　]+(?:\s+[^\s\n　]+)?)',
        r'名前[：:\s]*([^\s\n　]+(?:\s+[^\s\n　]+)?)',
        r'お名前[：:\s]*([^\s\n　]+)',
        r'候補者[：:\s]*([^\s\n　]+)',
        r'エンジニア[：:\s]*([^\s\n　]+)',
        r'要員[：:\s]*([^\s\n　]+)',
        r'【([^】]+)】.*?(?:様|さん)',
        r'([^\s　]{2,4})(?:様|さん)',
    ]
    for pattern in name_patterns:
        m = re.search(pattern, text)
        if m:
            name = m.group(1).strip()
            if len(name) >= 2 and len(name) <= 10:
                info['name'] = name
                break

    # スキルの抽出
    found_skills = []
    skill_patterns = {
        'Java': r'\bJava\b(?!Script)',
        'Python': r'\bPython\b',
        'PHP': r'\bPHP\b',
        'JavaScript': r'\bJavaScript\b|\bJS\b',
        'TypeScript': r'\bTypeScript\b|\bTS\b',
        'C#': r'\bC#\b',
        'Node.js': r'\bNode\.?js\b',
        'React': r'\bReact\b',
        'AWS': r'\bAWS\b',
        'インフラ': r'インフラ|Linux|ネットワーク',
    }
    for skill, pattern in skill_patterns.items():
        if re.search(pattern, text, re.IGNORECASE):
            found_skills.append(skill)
    if found_skills:
        info['skills'] = found_skills

    # 単価の抽出
    price_patterns = [
        r'単価[：:\s]*(\d+)万?',
        r'希望単価[：:\s]*(\d+)万?',
        r'(\d+)万円?/月',
        r'月単価[：:\s]*(\d+)',
    ]
    for pattern in price_patterns:
        m = re.search(pattern, text)
        if m:
            price = int(m.group(1))
            if 30 <= price <= 200:  # 妥当な範囲
                info['price'] = price
                break

    # 経験年数
    exp_patterns = [
        r'経験[：:\s]*(\d+)年',
        r'経験年数[：:\s]*(\d+)',
        r'(\d+)年経験',
        r'エンジニア歴[：:\s]*(\d+)年',
    ]
    for pattern in exp_patterns:
        m = re.search(pattern, text)
        if m:
            exp = int(m.group(1))
            if 0 <= exp <= 50:
                info['experience'] = exp
                break

    # 稼働可能日
    date_patterns = [
        r'稼働[可能]*日[：:\s]*(\d{4}[年/\-]\d{1,2}[月/\-]\d{1,2})',
        r'参画可能[：:\s]*(\d{4}[年/\-]\d{1,2}[月/\-]\d{1,2})',
        r'(\d{4})年(\d{1,2})月(?:(\d{1,2})日)?(?:より|から|稼働)',
        r'稼働[：:\s]*(\d{4})[年/](\d{1,2})[月/](\d{0,2})',
    ]
    for pattern in date_patterns:
        m = re.search(pattern, text)
        if m:
            try:
                if m.lastindex == 1:
                    date_str_raw = m.group(1)
                    date_str_raw = re.sub(r'(\d{4})年(\d{1,2})月(\d{1,2})日?',
                                         lambda x: f"{x.group(1)}-{int(x.group(2)):02d}-{int(x.group(3)):02d}",
                                         date_str_raw)
                    date_str_raw = date_str_raw.replace('/', '-')
                    info['available_date'] = date_str_raw[:10]
                else:
                    year = m.group(1)
                    month = m.group(2)
                    day = m.group(3) if m.lastindex >= 3 and m.group(3) else '01'
                    info['available_date'] = f"{year}-{int(month):02d}-{int(day) if day else 1:02d}"
            except:
                pass
            break

    # メールアドレス
    email_m = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    if email_m:
        found_email = email_m.group(0)
        if found_email != EMAIL_USER:
            info['email'] = found_email

    # 連絡先（電話番号）
    tel_m = re.search(r'(\d{2,4}[-\s]?\d{2,4}[-\s]?\d{3,4})', text)
    if tel_m:
        info['tel'] = tel_m.group(1)

    return info

def register_to_notion(info):
    """Notionにエンジニア情報を登録"""
    name = info.get('name', f"【{info.get('raw_subject', '件名不明')[:20]}】")

    note_parts = [
        f"送信者: {info.get('raw_sender', '')}",
        f"受信日: {info.get('raw_date', '')}",
        f"件名: {info.get('raw_subject', '')}",
        "",
        info.get('raw_body', '')
    ]
    note = "\n".join(note_parts)[:2000]

    properties = {
        "名前": {
            "title": [{"text": {"content": name}}]
        },
        "稼働状況": {
            "select": {"name": "稼働可能"}
        },
        "備考（LINEメモ）": {
            "rich_text": [{"text": {"content": note}}]
        }
    }

    if 'skills' in info:
        properties["スキル"] = {
            "multi_select": [{"name": s} for s in info['skills'] if s in VALID_SKILLS]
        }

    if 'price' in info:
        properties["単価（万円）"] = {"number": info['price']}

    if 'available_date' in info:
        properties["稼働可能日"] = {"date": {"start": info['available_date']}}

    if 'experience' in info:
        properties["経験年数"] = {"number": info['experience']}

    if 'tel' in info:
        properties["連絡先"] = {"phone_number": info['tel']}

    if 'email' in info:
        properties["メール"] = {"email": info['email']}

    res = requests.post(
        "https://api.notion.com/v1/pages",
        headers=NOTION_HEADERS,
        json={
            "parent": {"database_id": NOTION_ENGINEER_DB_ID},
            "properties": properties
        }
    )

    if res.status_code == 200:
        return True, name
    else:
        return False, f"エラー: {res.status_code} {res.text[:200]}"

def main():
    print("=" * 60)
    print("sessalesメール → Notion DB登録スクリプト")
    print("=" * 60)

    # IMAP接続
    print(f"\nIMAPサーバーに接続中: {IMAP_SERVER}:{IMAP_PORT}")
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(EMAIL_USER, EMAIL_PASS)
        print("✅ ログイン成功")
    except Exception as e:
        print(f"❌ 接続エラー: {e}")
        return

    # INBOXを選択
    mail.select("INBOX")

    # 過去3週間の日付
    since_date = (datetime.now() - timedelta(weeks=3)).strftime("%d-%b-%Y")
    print(f"\n検索期間: {since_date} 以降")

    # メール検索
    status, messages = mail.search(None, f'SINCE {since_date}')
    if status != 'OK':
        print("❌ メール検索失敗")
        return

    mail_ids = messages[0].split()
    print(f"📧 取得メール数: {len(mail_ids)}件")

    results = []
    registered = 0
    skipped = 0

    for i, mail_id in enumerate(mail_ids):
        try:
            status, msg_data = mail.fetch(mail_id, '(RFC822)')
            if status != 'OK':
                continue

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            subject = decode_str(msg.get('Subject', ''))
            sender = decode_str(msg.get('From', ''))
            date_str = msg.get('Date', '')
            body = get_email_body(msg)

            print(f"\n[{i+1}/{len(mail_ids)}] {subject[:40]}...")
            print(f"  送信者: {sender[:50]}")

            # 人材情報っぽいメールか判定
            keywords = ['エンジニア', '要員', '人材', 'スキル', '稼働', 'Java', 'Python',
                       'PHP', 'AWS', '経験', '単価', '候補', '技術者', 'SE', 'PG', 'プログラマ']
            text_to_check = f"{subject} {body[:300]}"
            is_engineer_email = any(kw in text_to_check for kw in keywords)

            if not is_engineer_email:
                print(f"  → スキップ（人材情報ではない）")
                skipped += 1
                continue

            # パース
            info = parse_engineer_from_email(subject, body, sender, date_str)

            # Notion登録
            success, result = register_to_notion(info)
            if success:
                print(f"  ✅ Notion登録: {result}")
                registered += 1
                results.append({'name': result, 'subject': subject, 'sender': sender})
            else:
                print(f"  ❌ 登録失敗: {result}")

        except Exception as e:
            print(f"  ❌ エラー: {e}")
            continue

    mail.logout()

    print("\n" + "=" * 60)
    print(f"完了！ 登録: {registered}件 / スキップ: {skipped}件 / 合計: {len(mail_ids)}件")
    print("=" * 60)

    # 結果をJSONに保存
    result_path = os.path.join(os.path.dirname(__file__), 'email_import_result.json')
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n結果を保存: {result_path}")

if __name__ == '__main__':
    main()
