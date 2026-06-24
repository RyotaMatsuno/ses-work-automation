"""
mail_pipeline.py - v6.0
v6からの変更:
- 受信メール全件をSQLite(raw_inbox.db)に保存（取りこぼしゼロ基盤）
- 分類をRecall重視に変更（project/skipの2値、engineerはskipに統合）
- 案件カテゴリ拡張（事務・ヘルプデスク・PMO等も全件取込）
- FETCH_LIMIT=200, PROCESS_LIMIT=50 フル復帰
- job_category/age_limit/headcount/commercial_flow フィールド追加
- processed_ids.json廃止→SQLiteのprocessedフラグに移行
"""

import base64
import email
import hashlib
import imaplib
import json
import mimetypes
import msvcrt
import os
import re
import smtplib
import socket
import ssl
import time

# skill_readerをインポート
import sys
from datetime import date, datetime, timedelta
from email import encoders
from email.header import decode_header
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import IO

import jpholiday
import requests
from dotenv import dotenv_values

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
sys.path.insert(0, str(Path(__file__).parent.parent))
from common.email_cleaner import clean_email_body
from common.ledger import can_spend
from common.ledger import record as ledger_record
from common.notion_register import NotionAPIError
from common.notion_register import register_project as notion_register_project
from cost_guard import allowed, finalize
from mail_pipeline.metrics_recorder import MetricsRecorder
from mail_pipeline.raw_inbox import (
    account_key_from_user,
    increment_retry_count,
    insert_raw_email,
    migrate_processed_ids_json,
    update_classify_result,
)
from mail_pipeline.raw_inbox import (
    init_db as init_raw_inbox_db,
)
from mail_pipeline.raw_inbox import (
    load_processed_ids as load_processed_ids_from_db,
)
from mail_pipeline.raw_inbox import (
    count_unprocessed,
)
from mail_pipeline.raw_inbox import (
    fetch_unprocessed_from_db,
)
from mail_pipeline.raw_inbox import (
    mark_processed as mark_processed_in_db,
)
from mail_pipeline.recovery_mode import (
    build_demote_message as _build_demote_message,
)
from mail_pipeline.recovery_mode import (
    build_promote_message as _build_promote_message,
)
from mail_pipeline.recovery_mode import (
    evaluate_promotion as _evaluate_promotion,
)
from mail_pipeline.recovery_mode import (
    get_limits as _get_recovery_limits,
)
from mail_pipeline.recovery_mode import (
    load_state as _load_recovery_state,
)
from mail_pipeline.price_extractor import resolve_final_price
from mail_pipeline.project_notion_save import (
    backfill_note_append,
    log_project_save_warnings,
    prepare_notion_project_fields,
)
from skill_reader.skill_reader import (
    extract_skills_from_image,
    extract_skills_from_text,
    extract_text_from_docx,
    extract_text_from_pdf,
    generate_iko_mail,
    match_skills,
    pdf_to_base64_image,
)
from skill_reader.skill_reader import get_active_projects as _get_active_projects

# ===== 設定 =====
BASE_DIR = Path(__file__).parent
ENV_PATH = BASE_DIR.parent / "config" / ".env"
DRAFTS_DIR = BASE_DIR / "pipeline_drafts"
LOG_PATH = BASE_DIR / "pipeline.log"
LOCK_FILE = os.path.join(os.environ.get("LOCALAPPDATA", ""), "ses_work_state", "pipeline.lock")
PROCESSED_IDS_PATH = BASE_DIR / "processed_ids.json"  # legacy; migrated to raw_inbox.db
RAW_INBOX_DB = BASE_DIR / "raw_inbox.db"
ATTACHMENTS_DIR = BASE_DIR.parent / "attachments"
SEND_COUNTER_PATH = BASE_DIR.parent / "config" / "send_counter.json"

# [COSTFIX] 取得・処理件数を制限してAPIコール暴走を防ぐ
FETCH_LIMIT = 200
PROCESS_LIMIT = 200  # FETCH_LIMITと同値。全件処理。CostGuard v2 fail-close=$8/日が安全弁
MATCH_TOP_N = 10

# payload検証: Notion API呼び出し前にtitleフィールドの存在を確認する
NOTION_FLAG_VALIDATE = os.environ.get("NOTION_FLAG_VALIDATE", "true").lower() == "true"

# 段階的復旧モード: RECOVERY_MODE=true 時に limits を recovery_state.json から読む
_RECOVERY_MODE = os.environ.get("RECOVERY_MODE", "false").lower() == "true"
DB_PROPERTY_CACHE = {}

config = dotenv_values(ENV_PATH)
for k, v in config.items():
    if k not in os.environ:
        os.environ[k] = v

IMAP_SERVER = os.environ.get("OUTLOOK_IMAP_SERVER", "mail65.onamae.ne.jp")
IMAP_PORT = int(os.environ.get("OUTLOOK_IMAP_PORT", 993))
IMAP_CANONICAL_HOST = os.environ.get("OUTLOOK_IMAP_TLS_HOSTNAME", "mail65.onamae.ne.jp")
IMAP_TIMEOUT = 30
IMAP_MAX_RETRIES = 3
EMAIL_USER = os.environ.get("OUTLOOK_EMAIL", "sessales@terra-ltd.co.jp")
EMAIL_PASS = os.environ.get("OUTLOOK_PASSWORD", "")

# マルチアカウント設定（松野・岡本個人アドレス追加対応）
EMAIL_ACCOUNTS = [
    {"user": EMAIL_USER, "password": EMAIL_PASS, "label": "共通メール"},
]
if os.environ.get("MATSUNO_EMAIL") and os.environ.get("MATSUNO_PASSWORD"):
    EMAIL_ACCOUNTS.append(
        {
            "user": os.environ["MATSUNO_EMAIL"],
            "password": os.environ["MATSUNO_PASSWORD"],
            "label": "松野メール",
        }
    )
if os.environ.get("OKAMOTO_EMAIL") and os.environ.get("OKAMOTO_PASSWORD"):
    EMAIL_ACCOUNTS.append(
        {
            "user": os.environ["OKAMOTO_EMAIL"],
            "password": os.environ["OKAMOTO_PASSWORD"],
            "label": "岡本メール",
        }
    )
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
NOTION_KEY = os.environ.get("NOTION_API_KEY", "")
ENGINEER_DB = os.environ.get("NOTION_ENGINEER_DB_ID", "")
PROJECT_DB = os.environ.get("NOTION_PROJECT_DB_ID", "")

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

VALID_SKILLS = [
    "Java",
    "Python",
    "PHP",
    "JavaScript",
    "TypeScript",
    "C#",
    "Node.js",
    "React",
    "AWS",
    "インフラ",
    "Go",
    "Ruby",
    "Swift",
    "Kotlin",
    "Vue.js",
    "Angular",
    "Docker",
    "Kubernetes",
    "GCP",
    "Azure",
    "Spring",
    "MySQL",
    "PostgreSQL",
    "Oracle",
    "MongoDB",
    "Linux",
]

VALID_JOB_CATEGORIES = {
    "development",
    "infrastructure",
    "pmo",
    "helpdesk",
    "office",
    "testing",
    "operations",
    "data",
    "sap",
    "other",
}

PROJECT_DB_REQUIRED_PROPERTIES = {
    "職種カテゴリ": {"select": {"options": [{"name": name} for name in sorted(VALID_JOB_CATEGORIES)]}},
    "年齢制限": {"rich_text": {}},
    "募集人数": {"number": {"format": "number"}},
    "商流": {"rich_text": {}},
}

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


def acquire_lock() -> IO[str]:
    """二重起動防止（Task Scheduler + 手動実行の排他）。"""
    os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)
    lock_fh = open(LOCK_FILE, "w", encoding="utf-8")
    try:
        msvcrt.locking(lock_fh.fileno(), msvcrt.LK_NBLCK, 1)
        return lock_fh
    except OSError:
        lock_fh.close()
        log("別プロセスが実行中 - スキップ")
        sys.exit(0)


def create_imap_ssl_context() -> ssl.SSLContext:
    """Create SSL context for IMAP. Verification enabled unless IMAP_SKIP_TLS_VERIFY=1."""
    ctx = ssl.create_default_context()
    if os.environ.get("IMAP_SKIP_TLS_VERIFY", "0") == "1":
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        log("WARNING: IMAP TLS verification disabled (IMAP_SKIP_TLS_VERIFY=1)")
    else:
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
    return ctx


def resolve_imap_connect_host(server: str) -> str:
    """Use hostname (not IP) for TLS when .env points at a bare IP address."""
    if re.fullmatch(r"\d+\.\d+\.\d+\.\d+", server or ""):
        return IMAP_CANONICAL_HOST
    return server


class _IMAP4SSLWithHostname(imaplib.IMAP4_SSL):
    """IMAP4_SSL that verifies certificate against tls_hostname (not connect host)."""

    def __init__(self, host: str, port: int, ssl_context: ssl.SSLContext, tls_hostname: str):
        self._tls_hostname = tls_hostname
        super().__init__(host, port, ssl_context=ssl_context)

    def _create_socket(self, timeout):
        sock = socket.create_connection((self.host, self.port), timeout)
        return self.ssl_context.wrap_socket(sock, server_hostname=self._tls_hostname)


def connect_imap(
    user: str,
    password: str,
    ssl_context: ssl.SSLContext | None = None,
) -> imaplib.IMAP4_SSL:
    """IMAP接続（タイムアウト + 指数バックオフリトライ）。"""
    last_error: Exception | None = None
    connect_host = resolve_imap_connect_host(IMAP_SERVER)
    tls_hostname = IMAP_CANONICAL_HOST if connect_host != IMAP_SERVER else connect_host
    for attempt in range(IMAP_MAX_RETRIES):
        try:
            socket.setdefaulttimeout(IMAP_TIMEOUT)
            mail = _IMAP4SSLWithHostname(
                connect_host,
                IMAP_PORT,
                ssl_context=ssl_context or create_imap_ssl_context(),
                tls_hostname=tls_hostname,
            )
            mail.login(user, password)
            return mail
        except (socket.timeout, imaplib.IMAP4.error, OSError) as e:
            last_error = e
            log(f"IMAP接続失敗 ({attempt + 1}/{IMAP_MAX_RETRIES}): {e}")
            if attempt < IMAP_MAX_RETRIES - 1:
                time.sleep(5 * (attempt + 1))
            else:
                raise
        finally:
            socket.setdefaulttimeout(None)
    if last_error is not None:
        raise last_error
    raise RuntimeError("IMAP接続に失敗しました")


def is_valid_iso_date(s) -> bool:
    if not s or not isinstance(s, str):
        return False
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}$", s.strip()))


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


# ===== 処理済みID管理（SQLite raw_inbox） =====
def load_processed_ids() -> set:
    try:
        return load_processed_ids_from_db(RAW_INBOX_DB)
    except Exception as e:
        log(f"processed_ids読み込みエラー: {e}")
    return set()


def save_processed_id(msg_id: str, processed: set | None, classify_result: str | None = None):
    if processed is not None:
        processed.add(msg_id)
    try:
        mark_processed_in_db(msg_id, classify_result=classify_result, db_path=RAW_INBOX_DB)
    except Exception as e:
        log(f"processed_ids保存エラー: {e}")


def maybe_save_processed_id(msg_id: str, processed: set | None, dry_run: bool = False) -> None:
    if not dry_run:
        save_processed_id(msg_id, processed)


def _notify_notion_retry_give_up(msg_id: str, subject: str, retry_count: int) -> None:
    """Notion登録が retry 上限に達したとき松野へ通知する。"""
    matsuno_uid = os.environ.get("MATSUNO_LINE_USER_ID", "Ue3508b43b84991f5a68281da5bf4cf39")
    message = (
        f"[mail_pipeline 再処理上限]\n"
        f"件名: {subject[:60]}\n"
        f"msg_id: {msg_id}\n"
        f"retry_count: {retry_count}\n"
        f"Notion登録失敗のため processed=1 にしました。手動確認してください。"
    )
    try:
        sys.path.insert(0, str(BASE_DIR.parent / "line_webhook"))
        from line_bridge import push_or_log

        push_or_log(matsuno_uid, message, task_id="mail_pipeline_notion_give_up")
    except Exception as exc:
        log(f"[Notion再処理上限] LINE通知失敗: {exc}")


def _prioritize_pending_work_items(work_items: list[dict], phase: str = "classify") -> dict[str, int]:
    """pending_queue に登録済みのメールを FIFO 順で先頭に並べ替える。"""
    pending_by_target: dict[str, int] = {}
    try:
        from common.ledger import fetch_pending_queue

        pending_entries = fetch_pending_queue(phase=phase, limit=500)
        pending_by_target = {e["target_id"]: e["id"] for e in pending_entries if e.get("target_id")}
        if not pending_by_target:
            return pending_by_target
        order = {target_id: idx for idx, target_id in enumerate(pending_by_target)}

        def _sort_key(em: dict) -> tuple[int, int]:
            msg_id = em.get("msg_id", "")
            if msg_id in order:
                return (0, order[msg_id])
            return (1, 0)

        work_items.sort(key=_sort_key)
        log(f"[pending_queue] {len(pending_by_target)}件を先頭に移動")
    except Exception as exc:
        log(f"[pending_queue] 優先ソートエラー: {exc}")
    return pending_by_target


def finalize_processed_state(
    msg_id: str,
    processed: set | None,
    classify_result: str | None,
    *,
    notion_register_failed: bool,
    subject: str = "",
) -> None:
    """Notion登録成否に応じて processed フラグを更新する。"""
    if notion_register_failed:
        retry_count = increment_retry_count(msg_id, db_path=RAW_INBOX_DB)
        log(f"Notion登録未完了のため再処理対象: {msg_id} (retry={retry_count})")
        if retry_count >= 3:
            log(f"retry_count上限到達のため processed=1: {msg_id}")
            save_processed_id(msg_id, processed, classify_result=classify_result)
            _notify_notion_retry_give_up(msg_id, subject, retry_count)
        return
    save_processed_id(msg_id, processed, classify_result=classify_result)


def get_unprocessed_count() -> int:
    """未処理メール件数（バックログ消化の進捗確認用）。"""
    try:
        return count_unprocessed(RAW_INBOX_DB)
    except Exception as e:
        log(f"未処理件数取得エラー: {e}")
        return 0


def ensure_raw_inbox_ready() -> None:
    init_raw_inbox_db(RAW_INBOX_DB)
    if PROCESSED_IDS_PATH.exists():
        try:
            migrated = migrate_processed_ids_json(
                processed_path=PROCESSED_IDS_PATH,
                db_path=RAW_INBOX_DB,
            )
            log(f"processed_ids.json → SQLite移行完了: 新規{migrated}件")
        except Exception as e:
            log(f"processed_ids移行エラー: {e}")


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
    "image/png",
    "image/jpeg",
    "image/jpg",
}

SKILL_SHEET_EXTENSIONS = {".pdf", ".docx", ".doc", ".png", ".jpg", ".jpeg"}


def get_body_and_attachments(msg):
    """本文テキストと添付スキルシート（バイナリ+MIMEタイプ）を取得"""
    body = ""
    attachments = []  # [{"data": bytes, "mime": str, "filename": str}]

    for part in msg.walk():
        content_type = part.get_content_type()
        disposition = str(part.get("Content-Disposition", ""))
        filename_raw = part.get_filename()
        filename = decode_str(filename_raw) if filename_raw else ""

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
        is_skill_sheet = content_type in SKILL_SHEET_MIME_TYPES or ext in SKILL_SHEET_EXTENSIONS

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


def fetch_emails_from_account(account: dict, limit: int, since_days: int = 7) -> list:
    """1アカウント分のメールを取得して返す"""
    user = account["user"]
    password = account["password"]
    label = account["label"]
    log(f"IMAP接続: {user} ({label})")
    ctx = create_imap_ssl_context()
    try:
        mail = connect_imap(user, password, ssl_context=ctx)
        mail.select("INBOX")
    except ssl.SSLError as e:
        log(f"IMAP TLS証明書検証エラー ({user}): {e}")
        return []
    except Exception as e:
        log(f"IMAP接続エラー ({user}): {e}")
        return []

    # [COSTFIX] 直近since_days日だけ取得して全件スキャンを避ける
    since_date = (date.today() - timedelta(days=since_days)).strftime("%d-%b-%Y")
    status, messages = mail.search(None, f"SINCE {since_date}")
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
            subject = decode_str(msg.get("Subject", ""))
            sender = decode_str(msg.get("From", ""))
            reply_to = decode_str(msg.get("Reply-To", "")) or sender
            msg_id = msg.get("Message-ID", f"no-id-{mail_id.decode()}-{user}")
            received_at = ""
            try:
                date_hdr = msg.get("Date", "")
                if date_hdr:
                    received_at = parsedate_to_datetime(date_hdr).isoformat()
            except Exception:
                received_at = datetime.now().isoformat()
            body, attachments = get_body_and_attachments(msg)
            attachment_names = [a.get("filename", "") for a in attachments if a.get("filename")]
            emails.append(
                {
                    "id": mail_id,
                    "msg_id": msg_id,
                    "subject": subject,
                    "sender": sender or user,
                    "reply_to": reply_to,
                    "body": body,
                    "attachments": attachments,
                    "attachment_names": attachment_names,
                    "received_at": received_at,
                    "account": account_key_from_user(user),
                    "account_label": label,
                }
            )
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
        emails = fetch_emails_from_account(account, limit, since_days=7)
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
    required = [s.lower() for s in project.get("required_skills", [])]
    optional = [s.lower() for s in project.get("optional_skills", [])]
    proj_price = project.get("price", 0) or 0
    scored = []
    for eng in engineers:
        eng_skills = [s.lower() for s in eng.get("skills", [])]
        eng_price = eng.get("price", 0) or 0
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
CLAUDE_MODEL = "claude-haiku-4-5-20251001"
MAIL_PIPELINE_BLOCK_TYPE = "mail_classify"


def _costguard_target_id(user: str, explicit: str = "") -> str:
    if explicit:
        return explicit
    return hashlib.sha256(user[:500].encode("utf-8", errors="replace")).hexdigest()[:32]


def _estimate_batch_tokens(batch_items: list[dict]) -> tuple[int, int]:
    est_in = 0
    est_out = 0
    for item in batch_items:
        params = item.get("params", {})
        messages = params.get("messages", [])
        content = messages[0].get("content", "") if messages else ""
        system = params.get("system", "")
        est_in += len(content) // 4 + len(system) // 4 + 100
        est_out += int(params.get("max_tokens", 50))
    return est_in, est_out


def _batch_budget_reserve(batch_items: list[dict], phase: str = "classify"):
    """Batch API 投入前に CostGuard v2 で予約する。成功時は reservation を保持して返す。"""
    if not batch_items:
        return None
    est_in, est_out = _estimate_batch_tokens(batch_items)
    if not can_spend(est_in, est_out, CLAUDE_MODEL):
        log("CostGuard blocked batch: budget")
        return None
    target_id = hashlib.sha256(
        ",".join(sorted(item.get("custom_id", "") for item in batch_items)).encode("utf-8")
    ).hexdigest()[:32]
    decision = allowed(
        phase=phase,
        block_type=MAIL_PIPELINE_BLOCK_TYPE,
        target_id=target_id,
        est_in=est_in,
        est_out=est_out,
        model_hint=CLAUDE_MODEL,
        script="mail_pipeline",
    )
    if decision.exit_code != 0 or not decision.allowed:
        log(f"CostGuard blocked batch: {decision.reason}")
        return None
    return decision


def _batch_budget_allowed(batch_items: list[dict], phase: str = "classify") -> bool:
    """後方互換ラッパー。"""
    return _batch_budget_reserve(batch_items, phase=phase) is not None


def _finalize_batch_usage(decision, items: list[dict], phase: str = "classify") -> None:
    """Batch API 完了後に reservation を finalize して実トークンを記録する。"""
    if not decision or not decision.allowed:
        return
    total_in = 0
    total_out = 0
    for item in items:
        usage = item.get("result", {}).get("message", {}).get("usage", {})
        if not usage:
            continue
        total_in += int(usage.get("input_tokens", 0))
        total_out += int(usage.get("output_tokens", 0))
    if total_in or total_out:
        finalize(decision, in_tokens=total_in, out_tokens=total_out, success=True)
    else:
        finalize(decision, success=False, error_kind="transient")


def _record_batch_item_usage(item: dict, phase: str = "classify") -> None:
    """単体テスト互換: 1件分のトークン集計ヘルパー（ledger 直接記録は廃止）。"""
    _ = phase
    usage = item.get("result", {}).get("message", {}).get("usage", {})
    if not usage:
        return


def call_claude(
    system: str,
    user: str,
    max_tokens: int = 1500,
    *,
    phase: str = "classify",
    target_id: str = "",
) -> str:
    decision = allowed(
        phase=phase,
        block_type=MAIL_PIPELINE_BLOCK_TYPE,
        target_id=_costguard_target_id(user, target_id),
        est_in=len(user) // 4 + 200,
        est_out=max_tokens,
        model_hint=CLAUDE_MODEL,
        script="mail_pipeline",
    )
    if decision.exit_code != 0:
        log(f"CostGuard blocked: {decision.reason}")
        return ""

    error_kind = ""
    in_tok = 0
    out_tok = 0
    response_text = ""
    try:
        res = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": CLAUDE_MODEL,
                "max_tokens": max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
            timeout=60,
        )
        if res.status_code == 200:
            data = res.json()
            usage = data.get("usage", {})
            in_tok = int(usage.get("input_tokens", 0))
            out_tok = int(usage.get("output_tokens", 0))
            response_text = data["content"][0]["text"]
        else:
            log(f"Claude APIエラー: {res.status_code} {res.text[:200]}")
            error_kind = "permanent_api"
    except Exception as e:
        log(f"Claude呼び出し例外: {e}")
        error_kind = "transient"
    finally:
        if decision.allowed:
            finalize(
                decision,
                in_tokens=in_tok,
                out_tokens=out_tok,
                success=(error_kind == ""),
                error_kind=error_kind,
            )
    return response_text


def classify_email(subject: str, body: str) -> dict:
    body = clean_email_body(body)
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


def _reclassify_by_rule(emails: list) -> tuple[dict[int, dict], int]:
    """other判定済みメールをルールベースのみで再分類（AI分類バッチは使わない）。"""
    from analyze_final import classify_by_rule

    results: dict[int, dict] = {}
    promoted = 0
    for i, em in enumerate(emails):
        subject = em.get("subject", "")
        body = em.get("body", "")
        sender = em.get("sender", "")
        rule_type = classify_by_rule(subject, sender, body)
        if rule_type == "project":
            info = classify_email(subject, body)
            if info.get("type") == "project":
                promoted += 1
            results[i] = info
        elif rule_type in ("skip", "engineer"):
            results[i] = {"type": "skip", "note": f"ルール再分類{rule_type}"}
        else:
            results[i] = {"type": "skip", "note": "ルール再分類unknown→skip"}
    log(f"再分類: {len(emails)}件試行 / project昇格{promoted}件")
    return results, promoted


def classify_email_v2(emails: list) -> dict:
    import time

    for em in emails:
        if em.get("body"):
            em["body"] = clean_email_body(em["body"])

    model = "claude-haiku-4-5-20251001"
    headers = {
        "x-api-key": ANTHROPIC_KEY,
        "anthropic-version": "2023-06-01",
        "anthropic-beta": "message-batches-2024-09-24",
        "content-type": "application/json",
    }
    classify_system = """あなたはSES業界のメール分類AIです。
件名と本文冒頭からemail_typeを判定し、JSONのみで返してください。

形式: {"type": "project"|"skip"}
※engineerは廃止。人員紹介メールはskipに統合

分類ルール:
- project: 業務委託・SES・派遣の案件情報。開発案件だけでなく、
  事務、ヘルプデスク、PMO、運用監視、キッティング、情シス支援、
  テスト、データ入力、コールセンター等も全て「project」。
  「案件」「募集」「○万」「○月〜」等のキーワードがあればproject。
  迷ったらprojectにする（Recall最優先）。
- skip: 以下は全てskip
  ・エンジニア/技術者/人材の紹介メール（「弊社エンジニア」「要員ご紹介」等）
  ・セミナー案内、メルマガ、配信停止通知、自動返信
  ・営業挨拶（案件情報なし）、求人広告、ニュースレター
  ※人員は松野/岡本がLINE経由で手動登録するため、配信の人員紹介は不要

SES業界用語:
- BP/プロパー/商流/稼働/並行 = SES業界の一般用語
- 案件 = 業務委託の仕事依頼
- 要員/人材 = エンジニア紹介"""
    project_system = """SES案件メールから情報をJSONのみで返してください。
{"type":"project","name":"案件名","job_category":"development|infrastructure|pmo|helpdesk|office|testing|operations|data|sap|other","required_skills":[],"optional_skills":[],"price":0,"start_date":"","location":"","remote":"不明","period":"","interview_count":1,"foreign_ok":false,"age_limit":"","headcount":1,"commercial_flow":"","note":"業務内容"}
job_category: 開発/インフラ/PMO/ヘルプデスク/事務/テスト/運用/データ/SAP/その他
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
                "messages": [{"role": "user", "content": f"件名: {subject}\n\n{body[:2000]}"}],
            },
        }

    def send_batch(batch_items: list) -> list:
        if not batch_items:
            return []
        decision = _batch_budget_reserve(batch_items, phase="classify")
        if decision is None:
            raise RuntimeError("CostGuard blocked batch")
        try:
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
            results = [json.loads(line) for line in lines]
            _finalize_batch_usage(decision, results, phase="classify")
            return results
        except Exception:
            finalize(decision, success=False, error_kind="transient")
            raise

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
        return {
            em.get("index", i): classify_email(em.get("subject", ""), em.get("body", "")) for i, em in enumerate(emails)
        }

    try:
        import sys as _sys

        _old_stdout = _sys.stdout
        try:
            import io as _io

            _sys.stdout = _io.StringIO()
            from analyze_final import ENGINEER_PATTERNS, PROJECT_PATTERNS, SKIP_PATTERNS, classify_by_rule, should_promote_other_to_project
        finally:
            _sys.stdout = _old_stdout
        _ = (SKIP_PATTERNS, ENGINEER_PATTERNS, PROJECT_PATTERNS)
    except Exception as e:
        log(f"  ルール分類インポート失敗: {e}")
        return {
            em.get("index", i): classify_email(em.get("subject", ""), em.get("body", "")) for i, em in enumerate(emails)
        }

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
            rule_type = classify_by_rule(subject, sender, body)
            if rule_type == "unknown":
                rule_type = "skip"
            if rule_type in ("skip", "engineer"):
                results[idx] = {"type": "skip", "note": f"ルール分類{rule_type}"}
            elif rule_type == "project":
                batch_requests.append(build_extract_request(f"extract_project_{idx}", subject, body, "project"))
            else:
                batch_requests.append(
                    {
                        "custom_id": f"classify_{idx}",
                        "params": {
                            "model": model,
                            "max_tokens": 50,
                            "system": classify_system,
                            "messages": [{"role": "user", "content": f"件名: {subject}\n本文: {body[:2000]}"}],
                        },
                    }
                )

        second_extract_requests = []
        for item in send_batch(batch_requests):
            custom_id = item.get("custom_id", "")
            text = result_text(item)
            parsed = parse_json_text(text)
            if custom_id.startswith("extract_project_"):
                idx = int(custom_id.rsplit("_", 1)[1])
                results[idx] = parsed
            elif custom_id.startswith("classify_"):
                idx = int(custom_id.rsplit("_", 1)[1])
                mail_type = parsed.get("type", "skip")
                if mail_type == "other":
                    em = email_by_index[idx]
                    if should_promote_other_to_project(em.get("subject", "")):
                        mail_type = "project"
                if mail_type in ("skip", "other", "engineer"):
                    results[idx] = {"type": "skip", "note": f"AI分類{mail_type}"}
                elif mail_type == "project":
                    em = email_by_index[idx]
                    second_extract_requests.append(
                        build_extract_request(
                            f"extract_project_{idx}", em.get("subject", ""), em.get("body", ""), "project"
                        )
                    )
                else:
                    results[idx] = {"type": "skip", "note": "AI分類不明"}

        for item in send_batch(second_extract_requests):
            custom_id = item.get("custom_id", "")
            if custom_id.startswith("extract_project_"):
                idx = int(custom_id.rsplit("_", 1)[1])
                results[idx] = parse_json_text(result_text(item))

        for i, em in enumerate(emails):
            idx = em.get("index", i)
            if idx not in results:
                results[idx] = {"type": "other", "note": "Batch結果なし"}
        return results
    except Exception as e:
        if "CostGuard blocked" in str(e):
            log(f"  CostGuard呼び出し上限: {len(batch_requests)}件をpending扱いに変更")
            for item in batch_requests:
                custom_id = item.get("custom_id", "")
                try:
                    idx = int(custom_id.rsplit("_", 1)[1])
                    if idx not in results:
                        results[idx] = {"type": "pending"}
                except (ValueError, IndexError):
                    pass
            for i, em in enumerate(emails):
                idx = em.get("index", i)
                if idx not in results:
                    results[idx] = {"type": "other", "note": "Batch結果なし"}
            return results
        log(f"  Batch API例外、個別分類へフォールバック: {e}")
        return {
            em.get("index", i): classify_email(em.get("subject", ""), em.get("body", "")) for i, em in enumerate(emails)
        }


def extract_affiliation(body: str) -> str:
    """メール本文から所属会社名を抽出。取れなければ空文字。"""
    if not ANTHROPIC_KEY or not body:
        return ""
    system = 'メール本文から送信元または紹介元の所属会社名だけを抽出し、JSONのみで返してください。形式: {"company":""}'
    result = call_claude(system, body[:2000], max_tokens=120, phase="extract")
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
    result = call_claude(system, json.dumps(payload, ensure_ascii=False), max_tokens=2000, phase="matching_pipeline")
    try:
        clean = re.sub(r"```json|```", "", result).strip()
        return json.loads(clean)
    except:
        return {"candidates": [], "proposal_draft": ""}


def double_check(text: str) -> str:
    return call_claude(DOUBLE_CHECK_SYSTEM, text, max_tokens=2000, phase="double_check")


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


def ensure_project_db_properties() -> None:
    """案件DBに職種カテゴリ等のプロパティがなければ追加する。"""
    if not PROJECT_DB:
        return
    if os.environ.get("DRY_RUN") == "1" and os.environ.get("DRY_RUN_PROCESS_EMAILS") != "1":
        return
    schema = get_database_property_names(PROJECT_DB)
    missing = {name: definition for name, definition in PROJECT_DB_REQUIRED_PROPERTIES.items() if name not in schema}
    if not missing:
        return
    try:
        res = requests.patch(
            f"https://api.notion.com/v1/databases/{PROJECT_DB}",
            headers=NOTION_HEADERS,
            json={"properties": missing},
            timeout=30,
        )
        if res.status_code == 200:
            DB_PROPERTY_CACHE[PROJECT_DB] = set(res.json().get("properties", {}).keys())
            log(f"案件DBプロパティ追加: {', '.join(missing.keys())}")
        else:
            log(f"案件DBプロパティ追加スキップ: {res.status_code} {res.text[:200]}")
    except Exception as e:
        log(f"案件DBプロパティ追加例外: {e}")


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
        r = requests.post(f"https://api.notion.com/v1/databases/{db_id}/query", headers=NOTION_HEADERS, json=payload)
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
        chunks.append({"text": {"content": text[i : i + chunk_size]}})
    return chunks or [{"text": {"content": ""}}]


def add_rich_text_if_exists(properties: dict, db_id: str, prop_name: str, text: str, chunked: bool = False):
    if prop_name in get_database_property_names(db_id):
        value = text or ""
        properties[prop_name] = {
            "rich_text": split_rich_text(value) if chunked else [{"text": {"content": value[:2000]}}]
        }


def add_url_if_exists(properties: dict, db_id: str, prop_name: str, url: str):
    if prop_name in get_database_property_names(db_id):
        properties[prop_name] = {"url": url or None}


def update_page_properties(page_id: str, properties: dict) -> bool:
    if not page_id or not properties:
        return True
    if os.environ.get("DRY_RUN") == "1":
        log(f"[DRY_RUN] Notion更新スキップ: page={page_id} props={list(properties.keys())}")
        return True
    res = requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=NOTION_HEADERS,
        json={"properties": properties},
        timeout=30,
    )
    if res.status_code != 200:
        log(f"  [Notion PATCH ERROR] {res.status_code}: {res.text[:300]}")
        return False
    return True


def save_attachments_for_page(page_id: str, attachments: list) -> list:
    if not page_id or not attachments:
        return []
    target_dir = ATTACHMENTS_DIR / page_id
    target_dir.mkdir(parents=True, exist_ok=True)
    saved_paths = []
    for idx, attachment in enumerate(attachments, 1):
        filename = attachment.get("filename") or f"attachment_{idx}"
        safe_name = re.sub(r'[\\/:*?"<>|]', "_", filename)
        path = target_dir / safe_name
        with open(path, "wb") as f:
            f.write(attachment.get("data", b""))
        saved_paths.append(str(path))
        log(f"  添付保存: {path}")
    return saved_paths


def collect_drive_url(body: str, saved_paths: list) -> str | None:
    try:
        from drive_uploader import extract_spreadsheet_url, upload_to_drive
    except Exception as e:
        log(f"  [Drive] import error: {e}")
        return None

    sheet_url = extract_spreadsheet_url(body)
    if sheet_url:
        log(f"  [Drive] spreadsheet URL抽出: {sheet_url}")
        return sheet_url

    for path in saved_paths:
        if Path(path).suffix.lower() in (".xlsx", ".xls"):
            try:
                drive_url = upload_to_drive(path)
                if drive_url:
                    log(f"  [Drive] Excelアップロード: {drive_url}")
                    return drive_url
            except Exception as e:
                log(f"  [Drive] upload error: {e}")
    return None


def load_send_counter() -> dict:
    try:
        if SEND_COUNTER_PATH.exists():
            with open(SEND_COUNTER_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {"matsuno": int(data.get("matsuno", 0)), "okamoto": int(data.get("okamoto", 0))}
    except Exception as e:
        log(f"send_counter読み込みエラー: {e}")
    return {"matsuno": 0, "okamoto": 0}


def save_send_counter(counter: dict):
    SEND_COUNTER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SEND_COUNTER_PATH, "w", encoding="utf-8") as f:
        json.dump(counter, f, ensure_ascii=False)


def choose_from_account(owner: str = "") -> str:
    owner = owner or ""
    if "松野" in owner:
        return "matsuno"
    if "岡本" in owner:
        return "okamoto"
    counter = load_send_counter()
    if counter["okamoto"] < counter["matsuno"] * 2 + 2:
        account = "okamoto"
    else:
        account = "matsuno"
    counter[account] += 1
    save_send_counter(counter)
    return account


def send_proposal_email(to_addr: str, subject: str, body: str, project: dict = None, engineer: dict = None) -> bool:
    project = project or {}
    engineer = engineer or {}
    owner = project.get("担当者") or project.get("owner") or project.get("assignee") or ""
    account = choose_from_account(owner)
    accounts_cfg = {
        "matsuno": {
            "user": "r-matsuno@terra-ltd.co.jp",
            "pw": os.environ.get("MATSUNO_MAIL_PASSWORD", os.environ.get("OUTLOOK_PASSWORD", "")),
        },
        "okamoto": {
            "user": "r-okamoto@terra-ltd.co.jp",
            "pw": os.environ.get("OKAMOTO_MAIL_PASSWORD", os.environ.get("OUTLOOK_PASSWORD", "")),
        },
        "sessales": {"user": EMAIL_USER, "pw": EMAIL_PASS},
    }
    acc = accounts_cfg.get(account, accounts_cfg["sessales"])
    original_message_id = project.get("元MessageID") or project.get("message_id") or ""
    original_body = project.get("案件情報原文") or project.get("raw_body") or ""
    if original_body:
        body = f"{body}\n\n------ 元のメッセージ ------\n{original_body}"

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = acc["user"]
    msg["To"] = to_addr
    if original_message_id:
        msg["In-Reply-To"] = original_message_id
        msg["References"] = original_message_id
    msg.attach(MIMEText(body, "plain", "utf-8"))

    attachment_path = engineer.get("添付ファイルパス") or engineer.get("attachment_path") or ""
    if attachment_path and Path(attachment_path).exists():
        ctype = mimetypes.guess_type(attachment_path)[0] or "application/octet-stream"
        maintype, subtype = ctype.split("/", 1)
        with open(attachment_path, "rb") as f:
            part = MIMEBase(maintype, subtype)
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", "attachment", filename=Path(attachment_path).name)
        msg.attach(part)

    if os.environ.get("DRY_RUN") == "1":
        log(f"[DRY_RUN] メール送信スキップ: from={acc['user']} to={to_addr} subject={subject}")
        return True
    if not acc["pw"]:
        log(f"メール送信エラー: パスワード未設定 account={account}")
        return False
    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(IMAP_SERVER, 465, context=ctx) as smtp:
        smtp.login(acc["user"], acc["pw"])
        smtp.sendmail(acc["user"], [to_addr], msg.as_bytes())
    return True


# ===== イニシャル・所属メール自動抽出ヘルパー =====
import re as _re

_INITIAL_DOT_RE = _re.compile(r"^[A-Z]\.[A-Z]$")
_INITIAL_PLAIN_RE = _re.compile(r"^[A-Z]{2,3}$")
_EXISTING_INITIAL_RE = _re.compile(r"^[A-Z\s.]{2,6}$")
_SKILL_CODE_RE = _re.compile(r"^(?=.*\d)(?=.*[A-Za-z])[A-Za-z0-9]{4,}$")
_SHORT_ASCII_RE = _re.compile(r"^[A-Z]{1,3}$")
_ANGLE_EMAIL_RE2 = _re.compile(r"<\s*([^<>\s]+@[^<>\s]+)\s*>")
_EMAIL_RE2 = _re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_COMPANY_KW = ["株式会社", "合同会社", "Inc", "Corp", "Ltd", "LLC", "エンジニア", "テック", "リンク", "ソリューション"]


def _derive_initial(name: str):
    """名前フィールドからイニシャルを生成。日本語名はNoneを返す。"""
    v = (name or "").strip()
    if not v:
        return None
    if _INITIAL_DOT_RE.fullmatch(v) or _INITIAL_PLAIN_RE.fullmatch(v) or _EXISTING_INITIAL_RE.fullmatch(v):
        return v
    if _SKILL_CODE_RE.fullmatch(v) or _SHORT_ASCII_RE.fullmatch(v):
        return None  # スキルコードは設定しない
    if _re.search(r"[^\x00-\x7f]", v):
        return None  # 日本語は手動
    if " " in v:
        parts = [p for p in v.split() if p]
        initials = [p[0].upper() for p in parts if _re.match(r"^[A-Za-z]", p)]
        if len(initials) >= 2:
            return ".".join(initials[:2])
    return None


def _looks_like_company(text: str) -> bool:
    if not text:
        return False
    if any(kw in text for kw in _COMPANY_KW):
        return True
    if _re.fullmatch(r"[A-Z]+", text):
        return True
    if " " not in text and "." in text:
        return True
    if _re.search(r"[\u30a0-\u30ff]", text):  # katakana
        return True
    return False


def _extract_affil_from_sender(sender: str):
    """Fromアドレス(sender)からメールアドレスと担当者名を抽出。"""
    if not sender:
        return None, None
    # Email extraction
    angle = _ANGLE_EMAIL_RE2.search(sender)
    email = None
    if angle:
        m = _EMAIL_RE2.search(angle.group(1))
        email = m.group(0) if m else None
    else:
        m = _EMAIL_RE2.search(sender)
        email = m.group(0) if m else None
    # Person name extraction
    angle_idx = sender.find("<")
    person = None
    if angle_idx > 0:
        before = sender[:angle_idx].strip().strip('"').strip("'")
        # Remove company in parens
        pm = _re.match(r"^(.*?)\s*[\(\uff08][^\)\uff09]+[\)\uff09]\s*$", before)
        if pm:
            before = pm.group(1).strip()
        if before and not _looks_like_company(before):
            person = before
    return email, person


# ===== end helpers =====


# ===== Notion payload validation (Feature Flag: NOTION_FLAG_VALIDATE) =====
def validate_engineer_payload(payload: dict) -> None:
    """engineer DB create前のpayload検証。デフォルトON。"""
    if not NOTION_FLAG_VALIDATE:
        return
    props = payload.get("properties", {})
    name_prop = props.get("名前")
    if not name_prop or "title" not in name_prop:
        raise ValueError("Notion payload validation: '名前' title is missing")
    title_arr = name_prop.get("title", [])
    if not title_arr or not title_arr[0].get("text", {}).get("content"):
        raise ValueError("Notion payload validation: '名前' title content is empty")


def validate_project_payload(payload: dict) -> None:
    """project DB create前のpayload検証。デフォルトON。"""
    if not NOTION_FLAG_VALIDATE:
        return
    props = payload.get("properties", {})
    name_prop = props.get("案件名")
    if not name_prop or "title" not in name_prop:
        raise ValueError("Notion payload validation: '案件名' title is missing")
    title_arr = name_prop.get("title", [])
    if not title_arr or not title_arr[0].get("text", {}).get("content"):
        raise ValueError("Notion payload validation: '案件名' title content is empty")


# ===== end validation =====


def register_project(
    info: dict,
    subject: str,
    sender: str,
    input_source: str = "",
    affiliation: str = "",
    raw_body: str = "",
    drive_url: str = None,
    message_id: str = "",
) -> tuple:
    name = info.get("name") or f"【{subject[:20]}】"
    note = f"[自動取込] 件名: {subject}\n送信元: {sender}\n\n{raw_body or info.get('note', '')}"
    properties = {
        "案件名": {"title": [{"text": {"content": name}}]},
        "ステータス": {"select": {"name": "募集中"}},
        "案件詳細": {"rich_text": split_rich_text(note)},
    }
    req, opt, final_price, location = prepare_notion_project_fields(info, subject, raw_body)
    if req:
        properties["必要スキル"] = {"multi_select": [{"name": s} for s in req]}
    if opt:
        properties["尚可スキル"] = {"multi_select": [{"name": s} for s in opt]}
    if final_price is not None:
        properties["単価（万円）"] = {"number": final_price}
    if location:
        properties["勤務地"] = {"rich_text": [{"text": {"content": str(location)[:2000]}}]}
    if is_valid_iso_date(info.get("start_date")):
        properties["開始日"] = {"date": {"start": info["start_date"].strip()}}
    job_category = str(info.get("job_category", "other") or "other").strip().lower()
    if job_category not in VALID_JOB_CATEGORIES:
        job_category = "other"
    if "職種カテゴリ" in get_database_property_names(PROJECT_DB):
        properties["職種カテゴリ"] = {"select": {"name": job_category}}
    add_rich_text_if_exists(properties, PROJECT_DB, "年齢制限", info.get("age_limit", ""))
    headcount = info.get("headcount")
    if headcount and "募集人数" in get_database_property_names(PROJECT_DB):
        try:
            properties["募集人数"] = {"number": int(headcount)}
        except (TypeError, ValueError):
            pass
    add_rich_text_if_exists(properties, PROJECT_DB, "商流", info.get("commercial_flow", ""))
    add_input_source_properties(properties, PROJECT_DB, input_source, affiliation)
    add_rich_text_if_exists(properties, PROJECT_DB, "元MessageID", message_id)
    add_rich_text_if_exists(properties, PROJECT_DB, "案件情報原文", raw_body or info.get("note", ""), chunked=True)
    if drive_url:
        add_url_if_exists(properties, PROJECT_DB, "DriveリンクURL", drive_url)
        if "Driveリンク" in get_database_property_names(PROJECT_DB):
            properties["Driveリンク"] = {"rich_text": [{"text": {"content": drive_url[:2000]}}]}
    if "matching_status" in get_database_property_names(PROJECT_DB):
        properties["matching_status"] = {"select": {"name": "pending"}}
    log_project_save_warnings(name, properties, subject, raw_body, log_fn=log)
    if os.environ.get("DRY_RUN") == "1":
        log(f"[DRY_RUN] 案件Notion登録スキップ: {name}")
        return True, "dry-run-project"
    payload = {"parent": {"database_id": PROJECT_DB}, "properties": properties}
    try:
        validate_project_payload(payload)
    except ValueError as ve:
        log(f"  [Notion PAYLOAD ERROR project] {ve}")
        return False, ""
    try:
        result = notion_register_project(properties, PROJECT_DB, headers=NOTION_HEADERS)
        if result.get("ok"):
            return True, result.get("page_id", "")
    except NotionAPIError as exc:
        log(f"  [Notion ERROR project] {exc.status}: {exc}")
        return False, ""
    except requests.RequestException as exc:
        log(f"  [Notion ERROR project] 通信失敗: {exc}")
        return False, ""
    except Exception as exc:
        log(f"  [Notion ERROR project] {exc}")
        return False, ""
    log("  [Notion ERROR project] registration failed")
    return False, ""


def register_engineer(
    info: dict,
    subject: str,
    sender: str,
    input_source: str = "",
    affiliation: str = "",
    drive_url: str = None,
    raw_body: str = "",
    attachment_path: str = "",
) -> tuple:
    """エンジニア登録、NotionページIDも返す"""
    name = info.get("name") or "（名前未記載）"
    note = f"[自動取込] 件名: {subject}\n送信元: {sender}\n\n{raw_body or info.get('note', '')}"
    properties = {
        "名前": {"title": [{"text": {"content": name}}]},
        "稼働状況": {"select": {"name": "稼働可能"}},
        "備考（LINEメモ）": {"rich_text": [{"text": {"content": note[:2000]}}]},
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
    # --- イニシャル自動生成 & 所属メール抽出 ---
    _initial = _derive_initial(name)
    if _initial:
        properties["イニシャル"] = {"rich_text": [{"text": {"content": _initial}}]}
    _aff_email, _aff_person = _extract_affil_from_sender(sender)
    if _aff_email:
        properties["所属メール"] = {"email": _aff_email}
    if _aff_person:
        properties["所属担当者名"] = {"rich_text": [{"text": {"content": _aff_person}}]}
    # --- end ---
    if drive_url:
        add_url_if_exists(properties, ENGINEER_DB, "DriveリンクURL", drive_url)
        if "Driveリンク" in get_database_property_names(ENGINEER_DB):
            properties["Driveリンク"] = {"rich_text": [{"text": {"content": drive_url[:2000]}}]}
    add_rich_text_if_exists(properties, ENGINEER_DB, "人員情報原文", raw_body or info.get("note", ""), chunked=True)
    add_rich_text_if_exists(properties, ENGINEER_DB, "添付ファイルパス", attachment_path)
    if os.environ.get("DRY_RUN") == "1":
        log(f"[DRY_RUN] 人材Notion登録スキップ: {name}")
        return True, "dry-run-engineer"
    payload = {"parent": {"database_id": ENGINEER_DB}, "properties": properties}
    try:
        validate_engineer_payload(payload)
    except ValueError as ve:
        log(f"  [Notion PAYLOAD ERROR engineer] {ve}")
        return False, ""
    res = requests.post(
        "https://api.notion.com/v1/pages",
        headers=NOTION_HEADERS,
        json=payload,
    )
    if res.status_code == 200:
        return True, res.json().get("id", "")
    log(f"  [Notion ERROR engineer] {res.status_code}: {res.text[:300]}")
    return False, ""


def get_available_engineers() -> list:
    pages = notion_query(ENGINEER_DB, {"property": "稼働状況", "select": {"equals": "稼働可能"}})
    engineers = []
    for p in pages:
        props = p["properties"]
        name_prop = props.get("名前", {}).get("title", [])
        name = name_prop[0]["plain_text"] if name_prop else "未記載"
        skills = [o["name"] for o in props.get("スキル", {}).get("multi_select", [])]
        price = props.get("単価（万円）", {}).get("number", 0) or 0
        avail = (props.get("稼働可能日", {}).get("date") or {}).get("start", "")
        note_prop = props.get("備考（LINEメモ）", {}).get("rich_text", [])
        note = note_prop[0]["plain_text"][:200] if note_prop else ""
        engineers.append({"name": name, "skills": skills, "price": price, "available_date": avail, "note": note})
    return engineers


# ===== スキルシート処理（v5新規）=====
def process_skill_sheet(attachment: dict, engineer_price: int = None, affiliation: str = "貴社") -> dict | None:
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

    just_count = sum(1 for r in match_results if r["proposable"] and r["gross"] and 5 <= r["gross"] <= 12)
    log(f"    照合完了: 提案可{sum(1 for r in match_results if r['proposable'])}件 (粗利ジャスト{just_count}件)")

    return {"info": info, "match_results": match_results, "iko_mail": iko_mail}


# ===== 下書き保存 =====
def save_draft(
    proj_name: str,
    reply_to: str,
    candidates: list,
    check_result: str,
    final_proposal: str,
    skill_result: dict = None,
    from_account: str = "sessales",
):
    DRAFTS_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = re.sub(r'[\\/:*?"<>|]', "_", proj_name)[:30]
    path = DRAFTS_DIR / f"{ts}_{safe_name}.txt"

    is_ok = "【判定】OK" in check_result

    content = f"""================================================================
提案文下書き v5
生成日時: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
================================================================
【案件名】{proj_name}
【返信先】{reply_to}
【送信アカウント】{from_account}

【候補者】
"""
    for i, c in enumerate(candidates[:3], 1):
        content += f"  {'①②③'[i - 1]} {c['name']} / {c.get('price', 0)}万円\n"
        content += f"     {c.get('summary', '')}\n"

    content += f"""
【ダブルチェック結果】
判定: {"[OK]" if is_ok else "[NG]"}
{check_result[:800]}

【提案メール本文（送信可能版）】
{final_proposal}
================================================================
"""

    # v5: スキルシート照合結果も付記
    if skill_result:
        just = [r for r in skill_result["match_results"] if r["proposable"] and r["gross"] and 5 <= r["gross"] <= 12]
        content += f"""
【スキルシート照合結果（skill_reader）】
氏名: {skill_result["info"].get("name", "不明")}
スキル: {", ".join(skill_result["info"].get("skills", []))}
レベル: {skill_result["info"].get("level", "不明")}

粗利ジャスト案件TOP:
"""
        for r in just[:3]:
            content += f"  {r['project_name']} | 粗利{r['gross']}万\n"

        content += f"""
【意向確認メール文面】
{skill_result["iko_mail"]}
================================================================
"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def save_engineer_draft(
    engineer_info: dict, match_results: list, iko_mail: str, reply_to: str, sender: str, from_account: str = "sessales"
):
    """人材メール専用の下書き保存"""
    DRAFTS_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = engineer_info.get("name", "不明")
    safe_name = re.sub(r'[\\/:*?"<>|]', "_", name)[:20]
    path = DRAFTS_DIR / f"{ts}_engineer_{safe_name}.txt"

    just = [r for r in match_results if r["proposable"] and r["gross"] and 5 <= r["gross"] <= 12]

    content = f"""================================================================
人材メール処理結果 v5
生成日時: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
================================================================
【エンジニア】{name}
【送信者】{sender}
【返信先】{reply_to}
【送信アカウント】{from_account}

【抽出スキル】{", ".join(engineer_info.get("skills", []))}
【レベル推定】{engineer_info.get("level", "不明")}
【概要】{engineer_info.get("summary", "")}

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
    lock_fh = acquire_lock()
    try:
        _main_impl()
    finally:
        lock_fh.close()


def _main_impl():
    log("=" * 50)

    # RecoveryMode: limits を動的に決定する
    _recovery_state = None
    fetch_limit = FETCH_LIMIT
    process_limit = PROCESS_LIMIT
    if _RECOVERY_MODE:
        try:
            _recovery_state = _load_recovery_state()
            process_limit, fetch_limit = _get_recovery_limits(_recovery_state)
            log(
                f"[RECOVERY] phase={_recovery_state['current_phase']} "
                f"process_limit={process_limit} fetch_limit={fetch_limit}"
            )
        except Exception as _re:
            log(f"[RECOVERY] state読み込み失敗（デフォルト使用）: {_re}")

    log("メールパイプライン v6.0 起動（SQLite全件保存・Recall重視分類・フル復帰）")
    log(f"設定: 取得{fetch_limit}件 / 処理{process_limit}件 / マッチング上位{MATCH_TOP_N}名")

    # Metrics 初期化
    metrics = MetricsRecorder()
    metrics.set("fetch_limit", fetch_limit)
    metrics.set("process_limit", process_limit)

    try:
        _main_body(metrics, fetch_limit, process_limit)
        final_metrics = metrics.finalize(exit_code=0)
    except Exception as top_ex:
        log(f"[FATAL] main例外: {top_ex}")
        final_metrics = metrics.finalize(exit_code=1, error_message=str(top_ex))

    # LINE push (毎回 + 異常時即時)
    _push_metrics_line(final_metrics)

    # RecoveryMode: 昇格/縮退評価
    if _RECOVERY_MODE and _recovery_state is not None:
        _handle_recovery(final_metrics, _recovery_state)

    remaining = get_unprocessed_count()
    log(f"残りバックログ: {remaining}件")

    log("=" * 50)


def _count_by_classify(classify_result_value, db_path=None):
    from mail_pipeline.raw_inbox import get_connection, init_db
    effective_db = db_path or RAW_INBOX_DB
    init_db(effective_db)
    conn = get_connection(effective_db)
    try:
        if classify_result_value is None:
            return conn.execute(
                "SELECT COUNT(*) FROM raw_emails WHERE processed=0 AND classify_result IS NULL"
            ).fetchone()[0]
        return conn.execute(
            "SELECT COUNT(*) FROM raw_emails WHERE processed=0 AND classify_result=?",
            (classify_result_value,),
        ).fetchone()[0]
    finally:
        conn.close()


def _save_all_emails_to_raw_inbox(emails: list) -> None:
    saved = 0
    for em in emails:
        try:
            if insert_raw_email(
                message_id=em.get("msg_id", ""),
                account=em.get("account", "sessales"),
                received_at=em.get("received_at", ""),
                sender=em.get("sender", ""),
                subject=em.get("subject", ""),
                body_text=em.get("body", ""),
                has_attachment=bool(em.get("attachments")),
                attachment_names=em.get("attachment_names", []),
                db_path=RAW_INBOX_DB,
            ):
                saved += 1
        except Exception as e:
            log(f"raw_inbox保存エラー ({em.get('msg_id', '')[:40]}): {e}")
    log(f"raw_inbox保存: 新規{saved}件 / 全{len(emails)}件")


def _main_body(metrics: "MetricsRecorder", fetch_limit: int, process_limit: int) -> None:
    if os.environ.get("DRY_RUN") == "1" and os.environ.get("DRY_RUN_PROCESS_EMAILS") != "1":
        log("[DRY_RUN] 外部取得・Notion書き込み・メール送信をスキップして起動確認完了")
        return
    null_backlog = _count_by_classify(None)
    if null_backlog > process_limit:
        expanded = min(null_backlog, 500)
        log(f"NULL backlog {null_backlog}件 > process_limit {process_limit} → {expanded}件に拡張")
        process_limit = expanded
        metrics.set("process_limit", process_limit)
    ensure_raw_inbox_ready()
    ensure_project_db_properties()

    # pending_queue: 失効処理 + 件数ログ
    try:
        from common.ledger import count_pending_queue, expire_old_pending
        expire_old_pending(7)
        _pq_classify = count_pending_queue(phase="classify")
        log(f"[pending_queue] classify: {_pq_classify}件")
    except Exception as _pq_err:
        log(f"[pending_queue] 確認エラー: {_pq_err}")

    emails = fetch_recent_emails(limit=fetch_limit)
    _pre_other = _count_by_classify("other")
    _pre_null = _count_by_classify(None)
    log(f"[DEBUG] pre-save: other={_pre_other} null={_pre_null}")
    _save_all_emails_to_raw_inbox(emails)
    _post_other = _count_by_classify("other")
    _post_null = _count_by_classify(None)
    log(f"[DEBUG] post-save: other={_post_other} null={_post_null} diff_other={_post_other-_pre_other} diff_null={_post_null-_pre_null}")
    metrics.set("accounts_fetched", len(EMAIL_ACCOUNTS))
    metrics.set("mails_fetched", len(emails))

    fresh_items, reclass_items = fetch_unprocessed_from_db(limit=process_limit, db_path=RAW_INBOX_DB)
    work_items = fresh_items + reclass_items
    log(f"[DEBUG] received: fresh={len(fresh_items)} reclass={len(reclass_items)} total={len(work_items)}")
    cr_dist: dict = {}
    for em in work_items:
        cr = em.get("classify_result")
        cr_dist[cr] = cr_dist.get(cr, 0) + 1
    log(f"[DEBUG] classify_result dist: {cr_dist}")

    metrics.set("mails_new", len(work_items))
    metrics.set("mails_fresh", len(fresh_items))
    metrics.set("mails_reclass", len(reclass_items))
    metrics.set("mails_skipped_dup", max(0, len(emails) - len(work_items)))
    log(
        f"DB work queue: {len(work_items)}件 "
        f"(fresh:{len(fresh_items)} / reclass:{len(reclass_items)})"
    )

    if not work_items:
        log("処理対象なし・終了")
        metrics.set("db_backlog_remaining", get_unprocessed_count())
        return

    all_classified: dict[int, dict] = {}
    reclass_promoted = 0
    target_offset = 0

    if fresh_items:
        fresh_results = classify_email_v2([{**em, "index": i} for i, em in enumerate(fresh_items)])
        for i in range(len(fresh_items)):
            all_classified[target_offset + i] = fresh_results.get(i, {"type": "other", "note": "分類失敗"})
        target_offset += len(fresh_items)

    if reclass_items:
        reclass_results, reclass_promoted = _reclassify_by_rule(reclass_items)
        for i in range(len(reclass_items)):
            all_classified[target_offset + i] = reclass_results.get(i, {"type": "skip", "note": "再分類失敗"})
        target_offset += len(reclass_items)

    metrics.set("reclass_attempted", len(reclass_items))
    metrics.set("reclass_promoted", reclass_promoted)

    target_emails = fresh_items + reclass_items
    for work_idx, em in enumerate(target_emails):
        em["_work_index"] = work_idx
    pending_by_target = _prioritize_pending_work_items(target_emails, phase="classify")
    engineers = get_available_engineers()
    log(f"エンジニアDB: {len(engineers)}名（稼働可能）")

    for em in target_emails:
        i = em["_work_index"]
        msg_id = em["msg_id"]
        subject = em["subject"]
        msg_type = "error"
        notion_register_failed = False
        try:
            sender = em["sender"]
            reply_to = em["reply_to"]
            body = em["body"]
            attachments = em.get("attachments", [])
            input_source = get_source_label(sender)

            log(f"処理中: {subject[:50]}")
            log(f"  入力元: {input_source}")
            if em.get("_source") == "db_backlog":
                log(f"  ソース: DB backlog (classify_result={em.get('classify_result')})")
            if attachments:
                log(f"  添付: {len(attachments)}件")

            info = all_classified.get(i) or classify_email(subject, body)
            msg_type = info.get("type", "skip")
            if msg_type == "engineer":
                msg_type = "skip"

            if msg_type == "pending":
                try:
                    from common.ledger import enqueue_pending as _enqueue_pending
                    from common.ledger import has_pending_target as _has_pending_target

                    if not _has_pending_target("classify", msg_id):
                        _enqueue_pending(
                            "classify",
                            block_type="mail_classify",
                            target_id=msg_id,
                            script="mail_pipeline",
                        )
                except Exception as _pq_err:
                    log(f"  pending_queue登録エラー: {_pq_err}")
                log(f"  pending_queue登録: {msg_id[:40]}")
                continue

            log(f"  判定: {msg_type}")
            update_classify_result(msg_id, msg_type, db_path=RAW_INBOX_DB)

            if msg_type == "project":
                project_owner = info.get("owner") or info.get("担当者") or info.get("project_owner") or input_source
                from_account = get_from_account(project_owner)
                log(f"  送信アカウント: {from_account}")
                affiliation = extract_affiliation(body)
                initial_drive_url = None
                try:
                    from drive_uploader import extract_spreadsheet_url

                    initial_drive_url = extract_spreadsheet_url(body)
                except Exception as e:
                    log(f"  [Drive] URL抽出スキップ: {e}")
                ok, notion_id = register_project(
                    info,
                    subject,
                    sender,
                    input_source,
                    affiliation,
                    raw_body=body,
                    drive_url=initial_drive_url,
                    message_id=msg_id,
                )
                proj_name = info.get("name") or subject[:30]
                if not ok:
                    log("  [NG] 案件Notion登録失敗")
                    metrics.inc("notion_errors")
                    notion_register_failed = True
                    continue
                metrics.inc("notion_project_created")
                log(f"  [OK] 案件登録: {proj_name}")

                saved_paths = save_attachments_for_page(notion_id, attachments)
                drive_url = initial_drive_url or collect_drive_url(body, saved_paths)
                if drive_url and drive_url != initial_drive_url:
                    props = {}
                    add_url_if_exists(props, PROJECT_DB, "DriveリンクURL", drive_url)
                    if "Driveリンク" in get_database_property_names(PROJECT_DB):
                        props["Driveリンク"] = {"rich_text": [{"text": {"content": drive_url[:2000]}}]}
                    update_page_properties(notion_id, props)

                filtered = filter_engineers_by_skills(info, engineers, top_n=3)
                log(f"  スキルフィルタ: {len(engineers)}名 → {len(filtered)}名")

                if not filtered:
                    log("  [!!] 候補者なし")
                    continue

                matching = ai_matching(info, filtered)
                candidates = matching.get("candidates", [])
                proposal_draft = matching.get("proposal_draft", "")

                if not candidates:
                    log("  [!!] AIマッチング候補なし")
                    continue
                log(f"  AIマッチング: {len(candidates)}名")

                check_input = f"【案件名】{proj_name}\n\n【提案文ドラフト】\n{proposal_draft}\n\n【候補者】\n"
                for c in candidates:
                    check_input += f"- {c['name']} / {c.get('price', 0)}万円 / 並行: {c.get('parallel', 'なし')}\n"
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
                    skill_result = process_skill_sheet(attachments[0], engineer_price=None, affiliation="貴社")

                draft_path = save_draft(
                    proj_name, reply_to, candidates, check_result, final_proposal, skill_result, from_account
                )
                log(f"  [OK] 提案文下書き保存: {draft_path.name}")

            elif msg_type == "skip":
                log(f"  スキップ: {subject[:40]}")

            else:
                log(f"  スキップ（その他）: {subject[:40]}")

        except Exception as ex:
            log(f"  [COSTFIX] 処理例外（スキップ）: {ex}")
        finally:
            if msg_type == "pending":
                pass
            else:
                finalize_processed_state(
                    msg_id,
                    None,
                    msg_type,
                    notion_register_failed=notion_register_failed,
                    subject=subject,
                )
                queue_id = pending_by_target.get(msg_id)
                if queue_id:
                    try:
                        from common.ledger import mark_pending_done

                        mark_pending_done(queue_id)
                    except Exception as _pq_done_err:
                        log(f"  pending_queue完了更新エラー: {_pq_done_err}")

    metrics.set("db_backlog_remaining", get_unprocessed_count())
    log("メールパイプライン v6.0 完了")


def _push_metrics_line(metrics: dict) -> None:
    """実行完了後に松野 LINE へメトリクス要約を push する。"""
    matsuno_uid = os.environ.get("MATSUNO_LINE_USER_ID", "Ue3508b43b84991f5a68281da5bf4cf39")
    has_error = metrics.get("exit_code", 0) != 0 or metrics.get("notion_errors", 0) > 0
    try:
        sys.path.insert(0, str(BASE_DIR.parent / "line_webhook"))
        from line_bridge import push_or_log

        ts = metrics.get("ts_start", "")[:16].replace("T", " ")
        hour_str = ts[11:13] if len(ts) > 13 else "??"
        status = "✅正常" if not has_error else "❌異常"
        err_note = f" / Notionエラー{metrics['notion_errors']}件" if metrics.get("notion_errors", 0) > 0 else ""
        fresh = metrics.get("mails_fresh", 0)
        reclass = metrics.get("mails_reclass", 0)
        promoted = metrics.get("reclass_promoted", 0)
        backlog = metrics.get("db_backlog_remaining", 0)
        msg = (
            f"[mail_pipeline {hour_str}:00台]\n"
            f"取得:{metrics.get('mails_fetched', 0)} "
            f"新規:{metrics.get('mails_new', 0)}(fresh:{fresh}+reclass:{reclass})\n"
            f"昇格:{promoted}件 残backlog:{backlog}件\n"
            f"Notion: eng={metrics.get('notion_engineer_created', 0)} "
            f"prj={metrics.get('notion_project_created', 0)}\n"
            f"所要:{metrics.get('elapsed_seconds', 0):.0f}秒 "
            f"cost:${metrics.get('cost_usd', 0.0):.4f}\n"
            f"{status}{err_note}"
        )
        push_or_log(matsuno_uid, msg, task_id="mail_pipeline_run")
    except Exception as e:
        log(f"[metrics] LINE push失敗（ログのみ）: {e}")


def _handle_recovery(metrics: dict, state: dict) -> None:
    """RecoveryMode: 昇格/縮退評価 + LINE通知。"""
    matsuno_uid = os.environ.get("MATSUNO_LINE_USER_ID", "Ue3508b43b84991f5a68281da5bf4cf39")
    prev_phase = state.get("current_phase", "day0_emergency")
    try:
        action = _evaluate_promotion(state, metrics)
        if action == "promote":
            msg = _build_promote_message(state)
            log(f"[RECOVERY] 昇格提案: {state.get('promotion_proposal_to')}")
            try:
                sys.path.insert(0, str(BASE_DIR.parent / "line_webhook"))
                from line_bridge import push_or_log

                push_or_log(matsuno_uid, msg, task_id="recovery_promote")
            except Exception as e:
                log(f"[RECOVERY] LINE push失敗: {e}")
        elif action == "demote":
            msg = _build_demote_message(state, prev_phase)
            log(f"[RECOVERY] 縮退実行: {prev_phase} → {state.get('current_phase')}")
            try:
                sys.path.insert(0, str(BASE_DIR.parent / "line_webhook"))
                from line_bridge import push_or_log

                push_or_log(matsuno_uid, msg, task_id="recovery_demote")
            except Exception as e:
                log(f"[RECOVERY] LINE push失敗: {e}")
    except Exception as e:
        log(f"[RECOVERY] 評価失敗: {e}")


if __name__ == "__main__":
    main()
