"""
mail_pipeline.py - v5.1
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

import jpholiday

# skill_readerをインポート
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).parent.parent))
from skill_reader.skill_reader import (
    extract_skills_from_text, extract_skills_from_image,
    extract_text_from_pdf, extract_text_from_docx, pdf_to_base64_image,
    get_active_projects as _get_active_projects, match_skills, generate_iko_mail
)
from usage_tracker.cost_logger import log_cost

# ===== 設定 =====
BASE_DIR = Path(__file__).parent
ENV_PATH = BASE_DIR.parent / "config" / ".env"
DRAFTS_DIR = BASE_DIR / "pipeline_drafts"
LOG_PATH = BASE_DIR / "pipeline.log"
PROCESSED_IDS_PATH = BASE_DIR / "processed_ids.json"

FETCH_LIMIT = 2000
PROCESS_LIMIT = 2000
MATCH_TOP_N = 10
DB_PROPERTY_CACHE = {}

config = dotenv_values(ENV_PATH)
for k, v in config.items():
    if k not in os.environ:
        os.environ[k] = v

IMAP_SERVER   = os.environ.get("OUTLOOK_IMAP_SERVER", "mail65.onamae.ne.jp")
IMAP_PORT     = int(os.environ.get("OUTLOOK_IMAP_PORT", 993))
EMAIL_USER    = os.environ.get("OUTLOOK_EMAIL", "sessales@terra-ltd.co.jp")
EMAIL_PASS    = os.environ.get("OUTLOOK_PASSWORD", "")

# マルチアカウント設定（松野・岡本個人アドレス追加対応）
EMAIL_ACCOUNTS = [
    {"user": EMAIL_USER, "password": EMAIL_PASS, "label": "共通メール"},
]
if os.environ.get("MATSUNO_EMAIL") and os.environ.get("MATSUNO_PASSWORD"):
    EMAIL_ACCOUNTS.append({
        "user": os.environ["MATSUNO_EMAIL"],
        "password": os.environ["MATSUNO_PASSWORD"],
        "label": "松野メール",
    })
if os.environ.get("OKAMOTO_EMAIL") and os.environ.get("OKAMOTO_PASSWORD"):
    EMAIL_ACCOUNTS.append({
        "user": os.environ["OKAMOTO_EMAIL"],
        "password": os.environ["OKAMOTO_PASSWORD"],
        "label": "岡本メール",
    })
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
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except (PermissionError, OSError):
        pass  # OneDrive同期ロック等でファイルが書けない場合はスキップ


def is_valid_iso_date(s) -> bool:
    if not s or not isinstance(s, str):
        return False
    return bool(re.match(r'^\d{4}-\d{2}-\d{2}$', s.strip()))


def get_source_label(from_addr: str) -> str:
    """Fromアドレスから入力元ラベルを返す"""
    from_addr_lower = (from_addr or "").lower()
    if "r-matsuno@" in from_addr_lower:
        return "松野メール"
    if "r-okamoto@" in from_addr_lower:
        return "岡本メール"
    if "sessales@" in from_addr_lower:
        return "共通メール"
    return "共通メール"


def get_from_account(owner: str) -> str:
    """案件担当者名から送信アカウント名を返す。"""
    if owner and "松野" in owner:
        return "matsuno"
    elif owner and "岡本" in owner:
        return "okamoto"
    return "sessales"


def get_input_source_label(email_user: str) -> str:
    """後方互換用。新規処理ではget_source_label(sender)を使う。"""
    return get_source_label(email_user)


def parse_notion_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
        if isinstance(parsed, datetime):
            return parsed
    except ValueError:
        return None
    return None


def is_within_business_days(created_time, n=4):
    created = parse_notion_datetime(created_time)
    if created is None:
        return False

    today = datetime.now(created.tzinfo).date() if created.tzinfo else datetime.now().date()
    count = 0
    d = created.date()
    while d <= today:
        if d.weekday() < 5 and not jpholiday.is_holiday(d):
            count += 1
        d += timedelta(days=1)
    return count <= n


def get_project_interview_datetime(project):
    props = project.get("properties", {})
    for key in ("interview_datetime", "面談日時", "面談日", "面談予定日時"):
        date_value = props.get(key, {}).get("date")
        if date_value and date_value.get("start"):
            return parse_notion_datetime(date_value["start"])
    return None


def is_project_active_by_deadline(project):
    interview_datetime = get_project_interview_datetime(project)
    if interview_datetime:
        now = datetime.now(interview_datetime.tzinfo) if interview_datetime.tzinfo else datetime.now()
        return now < interview_datetime - timedelta(hours=1)
    return is_within_business_days(project.get("created_time"), n=4)


def get_active_projects(filter_keyword: str = None) -> list:
    projects = _get_active_projects(filter_keyword)
    return [project for project in projects if is_project_active_by_deadline(project)]


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


def fetch_emails_from_account(account: dict, limit: int) -> list:
    """1アカウント分のメールを取得して返す"""
    user = account["user"]
    password = account["password"]
    label = account["label"]
    log(f"IMAP接続: {user} ({label})")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT, ssl_context=ctx)
        mail.login(user, password)
        mail.select("INBOX")
    except Exception as e:
        log(f"IMAP接続エラー ({user}): {e}")
        return []

    today_str = datetime.now().strftime("%d-%b-%Y")
    status, messages = mail.search(None, f"SINCE {today_str}")
    all_ids = messages[0].split() if status == "OK" and messages[0] else []
    if not all_ids:
        status, messages = mail.search(None, "ALL")
        all_ids = messages[0].split() if status == "OK" and messages[0] else []
    if not all_ids:
        log(f"  対象メールなし ({user})")
        mail.logout()
        return []

    target_ids = list(reversed(all_ids[-limit:]))
    log(f"  {user}: 全{len(all_ids)}件 → 最大{limit}件を処理対象")

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
            msg_id   = msg.get("Message-ID", f"no-id-{mail_id.decode()}-{user}")
            body, attachments = get_body_and_attachments(msg)
            emails.append({
                "id": mail_id, "msg_id": msg_id,
                "subject": subject,
                "sender": sender or user,  # Fromが空の場合はアカウントアドレスを使う
                "reply_to": reply_to,
                "body": body,
                "attachments": attachments,
                "account_label": label,  # どのアカウントから来たか記録
            })
        except Exception as e:
            log(f"メール取得エラー ({user}): {e}")

    mail.logout()
    return emails


def fetch_recent_emails(limit: int = 500) -> list:
    """全アカウントからメールを取得して返す（重複はmsg_idで除去）"""
    log(f"メール取得開始: {len(EMAIL_ACCOUNTS)}アカウント / 最大{limit}件/アカウント")
    seen_ids = set()
    all_emails = []
    for account in EMAIL_ACCOUNTS:
        if not account["password"]:
            log(f"  スキップ（パスワード未設定）: {account['user']}")
            continue
        emails = fetch_emails_from_account(account, limit)
        added = 0
        for em in emails:
            if em["msg_id"] not in seen_ids:
                seen_ids.add(em["msg_id"])
                all_emails.append(em)
                added += 1
        log(f"  {account['user']}: {added}件追加")
    log(f"取得完了: 合計{len(all_emails)}件")
    return all_emails


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
    model = "claude-haiku-4-5-20251001"
    try:
        res = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": model,
                "max_tokens": max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": user}]
            },
            timeout=60
        )
        if res.status_code == 200:
            data = res.json()
            usage = data.get("usage", {})
            log_cost(
                script_name="mail_pipeline",
                model=data.get("model") or model,
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
                cached_tokens=usage.get("cache_read_input_tokens", 0),
            )
            return data["content"][0]["text"]
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
    text = f"件名: {subject}\n\n{body[:200]}"
    result = call_claude(system, text)
    try:
        clean = re.sub(r"```json|```", "", result).strip()
        parsed = json.loads(clean)
        return parsed if isinstance(parsed, dict) else {"type": "other", "note": "予期しない形式"}
    except:
        return {"type": "other", "note": "解析失敗"}


def classify_email_v2(emails: list) -> dict:
    import contextlib
    import io
    import time

    model = "claude-haiku-4-5-20251001"
    headers = {
        "x-api-key": ANTHROPIC_KEY,
        "anthropic-version": "2023-06-01",
        "anthropic-beta": "message-batches-2024-09-24",
        "content-type": "application/json",
    }
    classify_system = """あなたはSES業界のメール分類AIです。件名と本文冒頭から email_type を判定し、JSONのみで返してください。
形式: {"type": "project"|"engineer"|"skip"|"other"}

SES業界用語:
- BP/プロパー/商流/稼働/並行 = SES業界の一般用語
- 案件 = 業務委託の仕事依頼
- 要員/人材 = エンジニア紹介

例:
入力: 件名「【案件】Java開発 渋谷 7月〜」 本文「お世話になっております。下記案件いかがでしょうか」
出力: {"type": "project"}

入力: 件名「弊社Java 3年 30万」 本文「いつもお世話になっております。弊社エンジニアをご紹介します」
出力: {"type": "engineer"}

入力: 件名「セミナーのご案内」 本文「AI活用セミナーのご案内です」
出力: {"type": "skip"}"""
    project_system = """SES案件メールから情報をJSONのみで返してください。
{"type":"project","name":"案件名","required_skills":[],"optional_skills":[],"price":0,"start_date":"","location":"","remote":"不明","period":"","interview_count":1,"foreign_ok":false,"note":"業務内容"}
価格は万円単位の整数。不明な項目は空文字または0。"""
    engineer_system = """SES人材メールから情報をJSONのみで返してください。
{"type":"engineer","name":"氏名","skills":[],"price":0,"available_date":"","experience_years":0,"company":"","note":"備考"}
価格は万円単位の整数。不明な項目は空文字または0。"""

    def parse_json_text(text: str) -> dict:
        try:
            clean = re.sub(r"```json|```", "", text or "").strip()
            parsed = json.loads(clean)
            return parsed if isinstance(parsed, dict) else {"type": "other", "note": "予期しない形式"}
        except Exception:
            return {"type": "other", "note": "解析失敗"}

    def build_extract_request(custom_id: str, subject: str, body: str, mail_type: str) -> dict:
        system = project_system if mail_type == "project" else engineer_system
        return {
            "custom_id": custom_id,
            "params": {
                "model": model,
                "max_tokens": 400,
                "system": system,
                "messages": [{"role": "user", "content": f"件名: {subject}\n\n{body[:200]}"}],
            },
        }

    def send_batch(batch_items: list) -> list:
        if not batch_items:
            return []
        res = requests_module.post(
            "https://api.anthropic.com/v1/messages/batches",
            headers=headers,
            json={"requests": batch_items},
            timeout=60,
        )
        if res.status_code not in (200, 201):
            raise RuntimeError(f"Batch作成エラー: {res.status_code} {res.text[:300]}")
        batch_id = res.json()["id"]
        log(f"  Batch API送信: {len(batch_items)}件 ({batch_id})")
        deadline = time.time() + 120 * 60
        while time.time() < deadline:
            status_res = requests_module.get(
                f"https://api.anthropic.com/v1/messages/batches/{batch_id}",
                headers=headers,
                timeout=60,
            )
            if status_res.status_code != 200:
                raise RuntimeError(f"Batch状態取得エラー: {status_res.status_code} {status_res.text[:300]}")
            status_data = status_res.json()
            if status_data.get("processing_status") == "ended":
                break
            time.sleep(30)
        else:
            raise TimeoutError(f"Batchタイムアウト: {batch_id}")

        results_res = requests_module.get(
            f"https://api.anthropic.com/v1/messages/batches/{batch_id}/results",
            headers=headers,
            timeout=120,
        )
        if results_res.status_code != 200:
            raise RuntimeError(f"Batch結果取得エラー: {results_res.status_code} {results_res.text[:300]}")
        lines = [line for line in results_res.text.splitlines() if line.strip()]
        return [json.loads(line) for line in lines]

    def result_text(item: dict) -> str:
        result = item.get("result", {})
        if result.get("type") != "succeeded":
            return ""
        content = result.get("message", {}).get("content", [])
        if content and isinstance(content[0], dict):
            return content[0].get("text", "")
        return ""

    if not ANTHROPIC_KEY:
        log("  Batch APIスキップ: ANTHROPIC_API_KEY未設定")
        return {em.get("index", i): classify_email(em.get("subject", ""), em.get("body", "")) for i, em in enumerate(emails)}

    try:
        with contextlib.redirect_stdout(io.StringIO()):
            from analyze_final import SKIP_PATTERNS, ENGINEER_PATTERNS, PROJECT_PATTERNS, classify_by_rule
        _ = (SKIP_PATTERNS, ENGINEER_PATTERNS, PROJECT_PATTERNS)
    except Exception as e:
        log(f"  ルール分類インポート失敗: {e}")
        return {em.get("index", i): classify_email(em.get("subject", ""), em.get("body", "")) for i, em in enumerate(emails)}

    requests_module = requests
    results = {}
    batch_requests = []
    email_by_index = {}

    try:
        for i, em in enumerate(emails):
            idx = em.get("index", i)
            subject = em.get("subject", "")
            sender = em.get("sender", "")
            body = em.get("body", "")
            email_by_index[idx] = em
            rule_type = classify_by_rule(subject, sender)
            if rule_type == "skip":
                results[idx] = {"type": "other", "note": "ルール分類skip"}
            elif rule_type in ("project", "engineer"):
                batch_requests.append(build_extract_request(f"extract_{rule_type}_{idx}", subject, body, rule_type))
            else:
                batch_requests.append({
                    "custom_id": f"classify_{idx}",
                    "params": {
                        "model": model,
                        "max_tokens": 50,
                        "system": classify_system,
                        "messages": [{"role": "user", "content": f"件名: {subject}\n本文: {body[:100]}"}],
                    },
                })

        second_extract_requests = []
        for item in send_batch(batch_requests):
            custom_id = item.get("custom_id", "")
            text = result_text(item)
            parsed = parse_json_text(text)
            if custom_id.startswith("extract_project_") or custom_id.startswith("extract_engineer_"):
                idx = int(custom_id.rsplit("_", 1)[1])
                results[idx] = parsed
            elif custom_id.startswith("classify_"):
                idx = int(custom_id.rsplit("_", 1)[1])
                mail_type = parsed.get("type", "other")
                if mail_type in ("skip", "other"):
                    results[idx] = {"type": "other", "note": "AI分類skip/other"}
                elif mail_type in ("project", "engineer"):
                    em = email_by_index[idx]
                    second_extract_requests.append(build_extract_request(f"extract_{mail_type}_{idx}", em.get("subject", ""), em.get("body", ""), mail_type))
                else:
                    results[idx] = {"type": "other", "note": "AI分類不明"}

        for item in send_batch(second_extract_requests):
            custom_id = item.get("custom_id", "")
            if custom_id.startswith("extract_project_") or custom_id.startswith("extract_engineer_"):
                idx = int(custom_id.rsplit("_", 1)[1])
                results[idx] = parse_json_text(result_text(item))

        for i, em in enumerate(emails):
            idx = em.get("index", i)
            if idx not in results:
                results[idx] = {"type": "other", "note": "Batch結果なし"}
        return results
    except Exception as e:
        log(f"  Batch API例外、個別分類へフォールバック: {e}")
        return {em.get("index", i): classify_email(em.get("subject", ""), em.get("body", "")) for i, em in enumerate(emails)}


def extract_affiliation(body: str) -> str:
    """メール本文から所属会社名を抽出。取れなければ空文字。"""
    if not ANTHROPIC_KEY or not body:
        return ""
    system = 'メール本文から送信元または紹介元の所属会社名だけを抽出し、JSONのみで返してください。形式: {"company":""}'
    result = call_claude(system, body[:2000], max_tokens=120)
    try:
        clean = re.sub(r"```json|```", "", result).strip()
        parsed = json.loads(clean)
        company = str(parsed.get("company", "")).strip() if isinstance(parsed, dict) else ""
        return company[:30]
    except Exception:
        return ""


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
def get_database_property_names(db_id: str) -> set:
    if not db_id:
        return set()
    if db_id not in DB_PROPERTY_CACHE:
        try:
            res = requests.get(
                f"https://api.notion.com/v1/databases/{db_id}",
                headers=NOTION_HEADERS,
                timeout=30,
            )
            if res.status_code == 200:
                DB_PROPERTY_CACHE[db_id] = set(res.json().get("properties", {}).keys())
            else:
                log(f"Notion DBプロパティ取得スキップ: {res.status_code} {res.text[:120]}")
                DB_PROPERTY_CACHE[db_id] = set()
        except Exception as e:
            log(f"Notion DBプロパティ取得例外: {e}")
            DB_PROPERTY_CACHE[db_id] = set()
    return DB_PROPERTY_CACHE[db_id]


def add_input_source_properties(properties: dict, db_id: str, input_source: str, affiliation: str):
    prop_names = get_database_property_names(db_id)
    if input_source and "入力元" in prop_names:
        properties["入力元"] = {"select": {"name": input_source}}
    if affiliation and "所属会社名" in prop_names:
        properties["所属会社名"] = {"rich_text": [{"text": {"content": affiliation[:500]}}]}


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



def split_rich_text(text: str, chunk_size: int = 1900) -> list:
    """Notionのrich_textは1ブロック2000文字上限のため複数ブロックに分割する"""
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunks.append({"text": {"content": text[i:i+chunk_size]}})
    return chunks or [{"text": {"content": ""}}]

def register_project(info: dict, subject: str, sender: str, input_source: str = "", affiliation: str = "", raw_body: str = "", drive_url: str = None) -> bool:
    name = info.get("name") or f"【{subject[:20]}】"
    note = f"【メールから自動登録】\n送信者: {sender}\n件名: {subject}\n\n{raw_body or info.get('note','')}"
    properties = {
        "案件名": {"title": [{"text": {"content": name}}]},
        "ステータス": {"select": {"name": "募集中"}},
        "案件詳細": {"rich_text": split_rich_text(note)}
    }
    req = [s for s in info.get("required_skills", []) if s in VALID_SKILLS]
    opt = [s for s in info.get("optional_skills", []) if s in VALID_SKILLS]
    if req:
        properties["必要スキル"] = {"multi_select": [{"name": s} for s in req]}
    if opt:
        properties["尚可スキル"] = {"multi_select": [{"name": s} for s in opt]}
    if info.get("price"):
        raw_price = info["price"]
        # Claudeが円単位で返すことがある（例: 750000）→ 万円単位に変換
        price_man = raw_price / 10000 if raw_price >= 1000 else raw_price
        properties["単価（万円）"] = {"number": price_man}
    if is_valid_iso_date(info.get("start_date")):
        properties["開始日"] = {"date": {"start": info["start_date"].strip()}}
    if info.get("location"):
        properties["勤務地"] = {"rich_text": [{"text": {"content": info["location"]}}]}
    add_input_source_properties(properties, PROJECT_DB, input_source, affiliation)
    if drive_url:
        properties["Driveリンク"] = {"rich_text": [{"text": {"content": drive_url[:2000]}}]}
    res = requests.post(
        "https://api.notion.com/v1/pages",
        headers=NOTION_HEADERS,
        json={"parent": {"database_id": PROJECT_DB}, "properties": properties}
    )
    return res.status_code == 200


def register_engineer(info: dict, subject: str, sender: str, input_source: str = "", affiliation: str = "", drive_url: str = None) -> tuple:
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
        raw_price = info["price"]
        # Claudeが円単位で返すことがある（例: 700000）→ 万円単位に変換
        price_man = raw_price / 10000 if raw_price >= 1000 else raw_price
        properties["単価（万円）"] = {"number": price_man}
    if is_valid_iso_date(info.get("available_date")):
        properties["稼働可能日"] = {"date": {"start": info["available_date"].strip()}}
    if info.get("experience_years"):
        properties["経験年数"] = {"number": info["experience_years"]}
    add_input_source_properties(properties, ENGINEER_DB, input_source, affiliation)
    if drive_url:
        properties["Driveリンク"] = {"rich_text": [{"text": {"content": drive_url[:2000]}}]}
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
               skill_result: dict = None, from_account: str = "sessales"):
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
【送信アカウント】{from_account}

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
                        iko_mail: str, reply_to: str, sender: str,
                        from_account: str = "sessales"):
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
【送信アカウント】{from_account}

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
    log("メールパイプライン v5.1 起動（入力元ラベル・所属会社名追加）")
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
    classified = classify_email_v2([
        {**em, "index": i} for i, em in enumerate(target_emails)
    ])
    engineers = get_available_engineers()
    log(f"エンジニアDB: {len(engineers)}名（稼働可能）")

    for i, em in enumerate(target_emails):
        subject     = em["subject"]
        sender      = em["sender"]
        reply_to    = em["reply_to"]
        body        = em["body"]
        msg_id      = em["msg_id"]
        attachments = em.get("attachments", [])
        input_source = get_source_label(sender)

        log(f"処理中: {subject[:50]}")
        log(f"  入力元: {input_source}")
        if attachments:
            log(f"  添付: {len(attachments)}件")

        info = classified.get(i) or classify_email(subject, body)
        msg_type = info.get("type", "other")
        log(f"  判定: {msg_type}")

        if msg_type == "project":
            project_owner = (
                info.get("owner") or info.get("担当者") or
                info.get("project_owner") or input_source
            )
            from_account = get_from_account(project_owner)
            log(f"  送信アカウント: {from_account}")
            affiliation = extract_affiliation(body)
            ok = register_project(info, subject, sender, input_source, affiliation, raw_body=body)
            proj_name = info.get("name") or subject[:30]
            if not ok:
                log(f"  [NG] 案件Notion登録失敗")
                save_processed_id(msg_id, processed)
                continue
            log(f"  [OK] 案件登録: {proj_name}")

            filtered = filter_engineers_by_skills(info, engineers, top_n=3)
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

            # Drive添付アップロード（案件メール添付）
            proj_drive_url = None
            if attachments:
                try:
                    from mail_pipeline.drive_uploader import upload_to_drive
                    att = attachments[0]
                    proj_drive_url = upload_to_drive(att["filename"], att["data"], att["mime"])
                    if proj_drive_url:
                        log(f"  [Drive] {proj_drive_url}")
                except Exception as _de:
                    log(f"  [Drive] upload error: {_de}")

            draft_path = save_draft(proj_name, reply_to, candidates,
                                    check_result, final_proposal, skill_result,
                                    from_account)
            log(f"  [OK] 提案文下書き保存: {draft_path.name}")

        elif msg_type == "engineer":
            # ===== v5: スキルシート添付対応 =====
            name = info.get("name", "（名前未記載）")
            eng_price = info.get("price") or None
            info_owner = (
                info.get("owner") or info.get("担当者") or
                info.get("project_owner") or input_source
            )
            from_account = get_from_account(info_owner)
            log(f"  送信アカウント: {from_account}")

            affiliation = extract_affiliation(body)
            skill_affiliation = affiliation or (sender.split("<")[0].strip() if "<" in sender else "貴社")

            skill_result = None

            # 添付スキルシートがある場合はskill_readerで処理
            if attachments:
                log(f"  添付スキルシートを処理: {attachments[0]['filename']}")
                skill_result = process_skill_sheet(
                    attachments[0],
                    engineer_price=eng_price,
                    affiliation=skill_affiliation
                )
                if skill_result:
                    # スキル抽出結果でinfo.skillsを上書き（より精度が高い）
                    info["skills"] = skill_result["info"].get("skills", info.get("skills", []))
                    log(f"  スキルシートからスキル上書き: {info['skills']}")

            # Drive添付アップロード
            drive_url = None
            if attachments:
                try:
                    from mail_pipeline.drive_uploader import upload_to_drive
                    att = attachments[0]
                    drive_url = upload_to_drive(att["filename"], att["data"], att["mime"])
                    if drive_url:
                        log(f"  [Drive] {drive_url}")
                except Exception as _de:
                    log(f"  [Drive] upload error: {_de}")

            # Notion登録
            ok, notion_id = register_engineer(info, subject, sender, input_source, affiliation, drive_url=drive_url)
            if ok:
                log(f"  [OK] 人材登録: {name} (Notion ID: {notion_id[:8]}...)")

                # skill_readerの結果があればNotionスキル欄も更新済み（register_engineerで登録）
                # 人材下書き保存
                if skill_result:
                    draft_path = save_engineer_draft(
                        skill_result["info"],
                        skill_result["match_results"],
                        skill_result["iko_mail"],
                        reply_to, sender, from_account
                    )
                    log(f"  [OK] 人材下書き保存: {draft_path.name}")
                    just = sum(1 for r in skill_result["match_results"]
                               if r["proposable"] and r["gross"] and 5 <= r["gross"] <= 12)
                    log(f"  粗利ジャスト案件: {just}件 → 意向確認文生成済み")
                else:
                    # 添付なし：本文から抽出した情報で照合のみ
                    projects = get_active_projects()
                    match_results = match_skills(info.get("skills", []), projects, eng_price)
                    iko_mail = generate_iko_mail(info, match_results, eng_price, skill_affiliation)
                    draft_path = save_engineer_draft(info, match_results, iko_mail, reply_to, sender, from_account)
                    log(f"  [OK] 本文ベース人材下書き保存: {draft_path.name}")
            else:
                log(f"  [NG] 人材Notion登録失敗: {name}")

        else:
            log(f"  スキップ（その他）: {subject[:40]}")

        save_processed_id(msg_id, processed)

    log("メールパイプライン v5.1 完了")
    log("=" * 50)


if __name__ == "__main__":
    main()
