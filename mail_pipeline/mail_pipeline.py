"""
mail_pipeline.py - v5
v4からの変更:
- 人材メール受信時: 添付スキルシート（PDF/Word/画像）を自動検出
- skill_readerでスキル抽出 → 案件照合 → 粗利ジャスト意向確認文生成
- 添付なし場合はメール本文からスキル抽出（従来通り）
- 案件登録時もskill_readerのget_active_projects/match_skillsを利用
"""

import imaplib
import email
import re
import json
import os
import ssl
import base64
import requests
from datetime import date, datetime, timedelta
from email.header import decode_header
from email.utils import parsedate_to_datetime
from dotenv import dotenv_values
from pathlib import Path

# skill_readerをインポート
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from skill_reader.skill_reader import (
    extract_skills_from_text, extract_skills_from_image,
    extract_text_from_pdf, extract_text_from_docx, pdf_to_base64_image,
    get_active_projects, match_skills, generate_iko_mail
)

# ===== 設定 =====
BASE_DIR = Path(__file__).parent
ENV_PATH = BASE_DIR.parent / "config" / ".env"
DRAFTS_DIR = BASE_DIR / "pipeline_drafts"
LOG_PATH = BASE_DIR / "pipeline.log"
PROCESSED_IDS_PATH = BASE_DIR / "processed_ids.json"

FETCH_LIMIT = 50
PROCESS_LIMIT = 20
MATCH_TOP_N = 10

config = dotenv_values(ENV_PATH)
for k, v in config.items():
    if k not in os.environ:
        os.environ[k] = v

IMAP_SERVER   = os.environ.get("OUTLOOK_IMAP_SERVER", "mail65.onamae.ne.jp")
IMAP_PORT     = int(os.environ.get("OUTLOOK_IMAP_PORT", 993))
EMAIL_USER    = os.environ.get("OUTLOOK_EMAIL", "sessales@terra-ltd.co.jp")
EMAIL_PASS    = os.environ.get("OUTLOOK_PASSWORD", "")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
NOTION_KEY    = os.environ.get("NOTION_API_KEY", "")
ENGINEER_DB   = os.environ.get("NOTION_ENGINEER_DB_ID", "")
PROJECT_DB    = os.environ.get("NOTION_PROJECT_DB_ID", "")

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

VALID_SKILLS = [
    "Java", "Python", "PHP", "JavaScript", "TypeScript", "C#", "Node.js",
    "React", "AWS", "インフラ", "Go", "Ruby", "Swift", "Kotlin", "Vue.js",
    "Angular", "Docker", "Kubernetes", "GCP", "Azure", "Spring",
    "MySQL", "PostgreSQL", "Oracle", "MongoDB", "Linux"
]

DOUBLE_CHECK_SYSTEM = f"""あなたはSES業界のダブルチェック専門AIです。
提案文と候補者情報を受け取り、以下のルールで厳密にチェックしてください。

今日の日付: {date.today().isoformat()}

【1. 除外ルール違反】
- 外国籍人材が含まれていないか
- 地方在住（関東以外）が含まれていないか
- 短期案件連続の人材が含まれていないか
- ブランクがある人材が含まれていないか
- 既往歴がある人材が含まれていないか

【2. 単価チェック（粗利）】
- 粗利 = 案件単価 - エンジニア単価
- 粗利5万円未満はNG / 粗利7万円以上が目標

【3. 並行スコア】
- 面談調整中:1.5 / 面談予定:2.0 / 結果待ち1-2日:2.5 / 3-7日:2.0 / 8-14日:1.5 / 15日超:1.0 / オファー中:5.0
- 合計5.0以上はNG

【4. 敬語・表現チェック】
- 「充足」→「全て満たしており」
- 「即戦力です」→「マッチ度高い人員かと存じます」

【5. 固有名詞マスキング】
- 企業名・担当者名・連絡先が残っていないか

出力フォーマット:
【判定】OK / NG
【チェック結果】
1. 除外ルール: OK/NG（理由）
2. 単価・粗利: OK/NG（詳細）
3. 並行スコア: OK/NG（詳細）
4. 敬語表現: OK/NG（修正箇所）
5. マスキング: OK/NG（漏れ箇所）
【修正済み提案文】
NGの場合は修正した提案文、OKの場合は「修正不要」
【所見】
気になる点があれば一言"""


# ===== ログ =====
def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def is_valid_iso_date(s) -> bool:
    if not s or not isinstance(s, str):
        return False
    return bool(re.match(r'^\d{4}-\d{2}-\d{2}$', s.strip()))


# ===== 処理済みID管理 =====
def load_processed_ids() -> set:
    try:
        if PROCESSED_IDS_PATH.exists():
            with open(PROCESSED_IDS_PATH, "r", encoding="utf-8") as f:
                return set(json.load(f))
    except Exception as e:
        log(f"processed_ids読み込みエラー: {e}")
    return set()


def save_processed_id(msg_id: str, processed: set):
    processed.add(msg_id)
    ids_list = list(processed)
    if len(ids_list) > 2000:
        ids_list = ids_list[1000:]
    try:
        with open(PROCESSED_IDS_PATH, "w", encoding="utf-8") as f:
            json.dump(ids_list, f, ensure_ascii=False)
    except Exception as e:
        log(f"processed_ids保存エラー: {e}")


# ===== メール取得（添付ファイル対応 v5新規）=====
def decode_str(s):
    if not s:
        return ""
    parts = decode_header(s)
    result = ""
    for part, charset in parts:
        if isinstance(part, bytes):
            result += part.decode(charset or "utf-8", errors="replace")
        else:
            result += str(part)
    return result


SKILL_SHEET_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "image/png", "image/jpeg", "image/jpg",
}

SKILL_SHEET_EXTENSIONS = {".pdf", ".docx", ".doc", ".png", ".jpg", ".jpeg"}


def get_body_and_attachments(msg):
    """本文テキストと添付スキルシート（バイナリ+MIMEタイプ）を取得"""
    body = ""
    attachments = []  # [{"data": bytes, "mime": str, "filename": str}]

    for part in msg.walk():
        content_type = part.get_content_type()
        disposition  = str(part.get("Content-Disposition", ""))
        filename_raw = part.get_filename()
        filename     = decode_str(filename_raw) if filename_raw else ""

        # 本文テキスト
        if content_type == "text/plain" and "attachment" not in disposition:
            charset = part.get_content_charset() or "utf-8"
            try:
                body = part.get_payload(decode=True).decode(charset, errors="replace")
            except Exception:
                pass
            continue

        # 添付ファイル判定
        ext = Path(filename).suffix.lower() if filename else ""
        is_skill_sheet = (
            content_type in SKILL_SHEET_MIME_TYPES or
            ext in SKILL_SHEET_EXTENSIONS
        )

        if is_skill_sheet and ("attachment" in disposition or filename):
            data = part.get_payload(decode=True)
            if data:
                # MIMEタイプを正規化
                mime = content_type
                if ext == ".pdf":
                    mime = "application/pdf"
                elif ext in (".docx", ".doc"):
                    mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                elif ext in (".png",):
                    mime = "image/png"
                elif ext in (".jpg", ".jpeg"):
                    mime = "image/jpeg"
                attachments.append({"data": data, "mime": mime, "filename": filename})
                log(f"    添付検出: {filename} ({mime}) {len(data)}bytes")

    return body.strip(), attachments


def fetch_recent_emails(limit: int = 50):
    log(f"IMAP接続開始（直近{limit}件取得）")
    ctx = ssl.create_default_context()
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT, ssl_context=ctx)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("INBOX")
    except Exception as e:
        log(f"IMAP接続エラー: {e}")
        return []

    status, messages = mail.search(None, "ALL")
    if status != "OK" or not messages[0]:
        log("対象メールなし")
        mail.logout()
        return []

    all_ids = messages[0].split()
    target_ids = list(reversed(all_ids[-limit:]))
    log(f"全件数: {len(all_ids)}件 → 直近{len(target_ids)}件を処理対象")

    emails = []
    for mail_id in target_ids:
        try:
            status, msg_data = mail.fetch(mail_id, "(RFC822)")
            if status != "OK":
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            subject  = decode_str(msg.get("Subject", ""))
            sender   = decode_str(msg.get("From", ""))
            reply_to = decode_str(msg.get("Reply-To", "")) or sender
            msg_id   = msg.get("Message-ID", f"no-id-{mail_id.decode()}")
            body, attachments = get_body_and_attachments(msg)
            emails.append({
                "id": mail_id, "msg_id": msg_id,
                "subject": subject, "sender": sender,
                "reply_to": reply_to, "body": body,
                "attachments": attachments  # v5追加
            })
        except Exception as e:
            log(f"メール取得エラー: {e}")

    mail.logout()
    log(f"取得完了: {len(emails)}件")
    return emails


# ===== スキルフィルタリング =====
def filter_engineers_by_skills(project: dict, engineers: list, top_n: int = MATCH_TOP_N) -> list:
    required  = [s.lower() for s in project.get("required_skills", [])]
    optional  = [s.lower() for s in project.get("optional_skills", [])]
    proj_price = project.get("price", 0) or 0
    scored = []
    for eng in engineers:
        eng_skills = [s.lower() for s in eng.get("skills", [])]
        eng_price  = eng.get("price", 0) or 0
        if proj_price > 0 and eng_price > 0 and abs(proj_price - eng_price) > 5:
            continue
        req_match = sum(1 for r in required if any(r in s for s in eng_skills))
        if required and req_match == 0:
            continue
        opt_match = sum(1 for o in optional if any(o in s for s in eng_skills))
        scored.append((req_match * 2 + opt_match, eng))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [eng for _, eng in scored[:top_n]]


# ===== Claude AI =====
def call_claude(system: str, user: str, max_tokens: int = 1500) -> str:
    try:
        res = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": user}]
            },
            timeout=60
        )
        if res.status_code == 200:
            return res.json()["content"][0]["text"]
        log(f"Claude APIエラー: {res.status_code} {res.text[:200]}")
        return ""
    except Exception as e:
        log(f"Claude呼び出し例外: {e}")
        return ""


def classify_email(subject: str, body: str) -> dict:
    system = """あなたはSES業界の情報解析AIです。メールを解析してJSON形式のみで返答してください。

案件情報の場合:
{"type":"project","name":"案件名","required_skills":["Java"],"optional_skills":[],"price":0,"start_date":"","location":"","remote":"不明","period":"","interview_count":1,"foreign_ok":false,"note":"業務内容"}

人材情報の場合:
{"type":"engineer","name":"氏名","skills":["Java"],"price":0,"available_date":"","experience_years":0,"company":"","note":"備考"}

どちらでもない場合:
{"type":"other","note":"内容要約"}"""
    text = f"件名: {subject}\n\n{body[:2000]}"
    result = call_claude(system, text)
    try:
        clean = re.sub(r"```json|```", "", result).strip()
        parsed = json.loads(clean)
        return parsed if isinstance(parsed, dict) else {"type": "other", "note": "予期しない形式"}
    except:
        return {"type": "other", "note": "解析失敗"}


def ai_matching(project: dict, engineers: list) -> dict:
    system = """あなたはSES業界のマッチングAIです。JSONで返してください。

除外ルール:
- 必須スキルに✕ → 除外
- 単価乖離5万超 → 除外

サマリー文（禁止: 充足・即戦力です）:
- 必須全○+尚可全○ → "必須・尚可ともにマッチ度高い人員"
- 必須全○+尚可○率50%以上 → "必須全て満たしており、尚可も○項目経験あり"
- 必須全○のみ → "必須スキル全て満たし即稼働可能"

返答フォーマット:
{"candidates":[{"name":"氏名","price":0,"summary":"サマリー","required_match":{},"optional_match":{},"parallel":"なし"}],"proposal_draft":"提案メール本文"}"""
    payload = {"project": project, "engineers": engineers}
    result = call_claude(system, json.dumps(payload, ensure_ascii=False), max_tokens=2000)
    try:
        clean = re.sub(r"```json|```", "", result).strip()
        return json.loads(clean)
    except:
        return {"candidates": [], "proposal_draft": ""}


def double_check(text: str) -> str:
    return call_claude(DOUBLE_CHECK_SYSTEM, text, max_tokens=2000)


# ===== Notion操作 =====
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


def register_project(info: dict, subject: str, sender: str) -> bool:
    name = info.get("name") or f"【{subject[:20]}】"
    note = f"【メールから自動登録】\n送信者: {sender}\n件名: {subject}\n\n{info.get('note','')}"
    properties = {
        "案件名": {"title": [{"text": {"content": name}}]},
        "ステータス": {"select": {"name": "募集中"}},
        "案件詳細": {"rich_text": [{"text": {"content": note[:2000]}}]}
    }
    req = [s for s in info.get("required_skills", []) if s in VALID_SKILLS]
    opt = [s for s in info.get("optional_skills", []) if s in VALID_SKILLS]
    if req:
        properties["必要スキル"] = {"multi_select": [{"name": s} for s in req]}
    if opt:
        properties["尚可スキル"] = {"multi_select": [{"name": s} for s in opt]}
    if info.get("price"):
        properties["単価（万円）"] = {"number": info["price"]}
    if is_valid_iso_date(info.get("start_date")):
        properties["開始日"] = {"date": {"start": info["start_date"].strip()}}
    if info.get("location"):
        properties["勤務地"] = {"rich_text": [{"text": {"content": info["location"]}}]}
    res = requests.post(
        "https://api.notion.com/v1/pages",
        headers=NOTION_HEADERS,
        json={"parent": {"database_id": PROJECT_DB}, "properties": properties}
    )
    return res.status_code == 200


def register_engineer(info: dict, subject: str, sender: str) -> tuple:
    """エンジニア登録、NotionページIDも返す"""
    name = info.get("name") or "（名前未記載）"
    note = f"【メールから自動登録】\n送信者: {sender}\n件名: {subject}\n\n{info.get('note','')}"
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
    if is_valid_iso_date(info.get("available_date")):
        properties["稼働可能日"] = {"date": {"start": info["available_date"].strip()}}
    if info.get("experience_years"):
        properties["経験年数"] = {"number": info["experience_years"]}
    res = requests.post(
        "https://api.notion.com/v1/pages",
        headers=NOTION_HEADERS,
        json={"parent": {"database_id": ENGINEER_DB}, "properties": properties}
    )
    if res.status_code == 200:
        return True, res.json().get("id", "")
    log(f"  [Notion ERROR engineer] {res.status_code}: {res.text[:300]}")
    return False, ""


def get_available_engineers() -> list:
    pages = notion_query(ENGINEER_DB, {
        "property": "稼働状況", "select": {"equals": "稼働可能"}
    })
    engineers = []
    for p in pages:
        props = p["properties"]
        name_prop = props.get("名前", {}).get("title", [])
        name   = name_prop[0]["plain_text"] if name_prop else "未記載"
        skills = [o["name"] for o in props.get("スキル", {}).get("multi_select", [])]
        price  = props.get("単価（万円）", {}).get("number", 0) or 0
        avail  = (props.get("稼働可能日", {}).get("date") or {}).get("start", "")
        note_prop = props.get("備考（LINEメモ）", {}).get("rich_text", [])
        note   = note_prop[0]["plain_text"][:200] if note_prop else ""
        engineers.append({"name": name, "skills": skills, "price": price,
                          "available_date": avail, "note": note})
    return engineers


# ===== スキルシート処理（v5新規）=====
def process_skill_sheet(attachment: dict, engineer_price: int = None,
                        affiliation: str = "貴社") -> dict | None:
    """
    添付スキルシートを処理してスキル抽出・案件照合・意向確認文を生成する。
    Returns: {"info": dict, "match_results": list, "iko_mail": str} or None
    """
    data = attachment["data"]
    mime = attachment["mime"]
    fname = attachment["filename"]

    log(f"    スキルシート処理中: {fname}")
    info = None

    try:
        if mime == "application/pdf":
            text = extract_text_from_pdf(data)
            if text:
                info = extract_skills_from_text(text)
            else:
                log("    (テキストなし → 画像変換)")
                b64img = pdf_to_base64_image(data)
                if b64img:
                    info = extract_skills_from_image(b64img, "image/png")
        elif "word" in mime:
            text = extract_text_from_docx(data)
            info = extract_skills_from_text(text)
        elif mime.startswith("image/"):
            b64 = base64.standard_b64encode(data).decode()
            info = extract_skills_from_image(b64, mime)
    except Exception as e:
        log(f"    スキルシート処理エラー: {e}")
        return None

    if not info:
        log("    スキル抽出失敗")
        return None

    log(f"    抽出スキル: {', '.join(info.get('skills', []))}")

    # 案件照合
    projects = get_active_projects()
    match_results = match_skills(info.get("skills", []), projects, engineer_price)

    # 意向確認メール生成
    iko_mail = generate_iko_mail(info, match_results, engineer_price, affiliation)

    just_count = sum(1 for r in match_results
                     if r["proposable"] and r["gross"] and 5 <= r["gross"] <= 12)
    log(f"    照合完了: 提案可{sum(1 for r in match_results if r['proposable'])}件 "
        f"(粗利ジャスト{just_count}件)")

    return {"info": info, "match_results": match_results, "iko_mail": iko_mail}


# ===== 下書き保存 =====
def save_draft(proj_name: str, reply_to: str, candidates: list,
               check_result: str, final_proposal: str,
               skill_result: dict = None):
    DRAFTS_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = re.sub(r'[\\/:*?"<>|]', '_', proj_name)[:30]
    path = DRAFTS_DIR / f"{ts}_{safe_name}.txt"

    is_ok = "【判定】OK" in check_result

    content = f"""================================================================
提案文下書き v5
生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
================================================================
【案件名】{proj_name}
【返信先】{reply_to}

【候補者】
"""
    for i, c in enumerate(candidates[:3], 1):
        content += f"  {'①②③'[i-1]} {c['name']} / {c.get('price',0)}万円\n"
        content += f"     {c.get('summary','')}\n"

    content += f"""
【ダブルチェック結果】
判定: {'[OK]' if is_ok else '[NG]'}
{check_result[:800]}

【提案メール本文（送信可能版）】
{final_proposal}
================================================================
"""

    # v5: スキルシート照合結果も付記
    if skill_result:
        just = [r for r in skill_result["match_results"]
                if r["proposable"] and r["gross"] and 5 <= r["gross"] <= 12]
        content += f"""
【スキルシート照合結果（skill_reader）】
氏名: {skill_result['info'].get('name', '不明')}
スキル: {', '.join(skill_result['info'].get('skills', []))}
レベル: {skill_result['info'].get('level', '不明')}

粗利ジャスト案件TOP:
"""
        for r in just[:3]:
            content += f"  {r['project_name']} | 粗利{r['gross']}万\n"

        content += f"""
【意向確認メール文面】
{skill_result['iko_mail']}
================================================================
"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def save_engineer_draft(engineer_info: dict, match_results: list,
                        iko_mail: str, reply_to: str, sender: str):
    """人材メール専用の下書き保存"""
    DRAFTS_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = engineer_info.get("name", "不明")
    safe_name = re.sub(r'[\\/:*?"<>|]', '_', name)[:20]
    path = DRAFTS_DIR / f"{ts}_engineer_{safe_name}.txt"

    just = [r for r in match_results
            if r["proposable"] and r["gross"] and 5 <= r["gross"] <= 12]

    content = f"""================================================================
人材メール処理結果 v5
生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
================================================================
【エンジニア】{name}
【送信者】{sender}
【返信先】{reply_to}

【抽出スキル】{', '.join(engineer_info.get('skills', []))}
【レベル推定】{engineer_info.get('level', '不明')}
【概要】{engineer_info.get('summary', '')}

【粗利ジャスト案件（5〜12万）TOP{len(just)}件】
"""
    for r in just[:5]:
        req_str = "  ".join(f"{s}:{'○' if v else '×'}" for s, v in r["required"].items()) or "なし"
        content += f"  {r['project_name']} ({r['client']}) | {r['project_price']}万 | 粗利{r['gross']}万\n"
        content += f"    必須: {req_str}\n"

    content += f"""
【意向確認メール文面（粗利ジャストTOP3）】
{iko_mail}
================================================================
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


# ===== メイン =====
def main():
    log("=" * 50)
    log("メールパイプライン v5 起動（スキルシート自動読み取り追加）")
    log(f"設定: 取得{FETCH_LIMIT}件 / 処理{PROCESS_LIMIT}件 / マッチング上位{MATCH_TOP_N}名")

    processed = load_processed_ids()
    log(f"処理済みID: {len(processed)}件")

    emails = fetch_recent_emails(limit=FETCH_LIMIT)
    if not emails:
        log("処理対象なし・終了")
        return

    new_emails = [e for e in emails if e["msg_id"] not in processed]
    log(f"新規処理対象: {len(new_emails)}件")

    if not new_emails:
        log("全て処理済み・終了")
        return

    target_emails = new_emails[:PROCESS_LIMIT]
    engineers = get_available_engineers()
    log(f"エンジニアDB: {len(engineers)}名（稼働可能）")

    for em in target_emails:
        subject     = em["subject"]
        sender      = em["sender"]
        reply_to    = em["reply_to"]
        body        = em["body"]
        msg_id      = em["msg_id"]
        attachments = em.get("attachments", [])

        log(f"処理中: {subject[:50]}")
        if attachments:
            log(f"  添付: {len(attachments)}件")

        info = classify_email(subject, body)
        msg_type = info.get("type", "other")
        log(f"  判定: {msg_type}")

        if msg_type == "project":
            ok = register_project(info, subject, sender)
            proj_name = info.get("name") or subject[:30]
            if not ok:
                log(f"  [NG] 案件Notion登録失敗")
                save_processed_id(msg_id, processed)
                continue
            log(f"  [OK] 案件登録: {proj_name}")

            filtered = filter_engineers_by_skills(info, engineers, top_n=MATCH_TOP_N)
            log(f"  スキルフィルタ: {len(engineers)}名 → {len(filtered)}名")

            if not filtered:
                log(f"  [!!] 候補者なし")
                save_processed_id(msg_id, processed)
                continue

            matching = ai_matching(info, filtered)
            candidates = matching.get("candidates", [])
            proposal_draft = matching.get("proposal_draft", "")

            if not candidates:
                log(f"  [!!] AIマッチング候補なし")
                save_processed_id(msg_id, processed)
                continue
            log(f"  AIマッチング: {len(candidates)}名")

            check_input = f"【案件名】{proj_name}\n\n【提案文ドラフト】\n{proposal_draft}\n\n【候補者】\n"
            for c in candidates:
                check_input += f"- {c['name']} / {c.get('price',0)}万円 / 並行: {c.get('parallel','なし')}\n"
            check_result = double_check(check_input)

            final_proposal = proposal_draft
            marker = "【修正済み提案文】"
            if marker in check_result:
                after = check_result.split(marker, 1)[1].strip()
                if "【所見】" in after:
                    after = after.split("【所見】")[0].strip()
                if after and after != "修正不要":
                    final_proposal = after

            # 案件メールにも添付スキルシートがある場合は処理
            skill_result = None
            if attachments:
                skill_result = process_skill_sheet(
                    attachments[0],
                    engineer_price=None,
                    affiliation="貴社"
                )

            draft_path = save_draft(proj_name, reply_to, candidates,
                                    check_result, final_proposal, skill_result)
            log(f"  [OK] 提案文下書き保存: {draft_path.name}")

        elif msg_type == "engineer":
            # ===== v5: スキルシート添付対応 =====
            name = info.get("name", "（名前未記載）")
            eng_price = info.get("price") or None

            # 所属会社名をsenderから抽出（簡易）
            affiliation = sender.split("<")[0].strip() if "<" in sender else "貴社"

            skill_result = None

            # 添付スキルシートがある場合はskill_readerで処理
            if attachments:
                log(f"  添付スキルシートを処理: {attachments[0]['filename']}")
                skill_result = process_skill_sheet(
                    attachments[0],
                    engineer_price=eng_price,
                    affiliation=affiliation
                )
                if skill_result:
                    # スキル抽出結果でinfo.skillsを上書き（より精度が高い）
                    info["skills"] = skill_result["info"].get("skills", info.get("skills", []))
                    log(f"  スキルシートからスキル上書き: {info['skills']}")

            # Notion登録
            ok, notion_id = register_engineer(info, subject, sender)
            if ok:
                log(f"  [OK] 人材登録: {name} (Notion ID: {notion_id[:8]}...)")

                # skill_readerの結果があればNotionスキル欄も更新済み（register_engineerで登録）
                # 人材下書き保存
                if skill_result:
                    draft_path = save_engineer_draft(
                        skill_result["info"],
                        skill_result["match_results"],
                        skill_result["iko_mail"],
                        reply_to, sender
                    )
                    log(f"  [OK] 人材下書き保存: {draft_path.name}")
                    just = sum(1 for r in skill_result["match_results"]
                               if r["proposable"] and r["gross"] and 5 <= r["gross"] <= 12)
                    log(f"  粗利ジャスト案件: {just}件 → 意向確認文生成済み")
                else:
                    # 添付なし：本文から抽出した情報で照合のみ
                    projects = get_active_projects()
                    match_results = match_skills(info.get("skills", []), projects, eng_price)
                    iko_mail = generate_iko_mail(info, match_results, eng_price, affiliation)
                    draft_path = save_engineer_draft(info, match_results, iko_mail, reply_to, sender)
                    log(f"  [OK] 本文ベース人材下書き保存: {draft_path.name}")
            else:
                log(f"  [NG] 人材Notion登録失敗: {name}")

        else:
            log(f"  スキップ（その他）: {subject[:40]}")

        save_processed_id(msg_id, processed)

    log("メールパイプライン v5 完了")
    log("=" * 50)


if __name__ == "__main__":
    main()
