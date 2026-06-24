# -*- coding: utf-8 -*-
"""
過去配信メールから40万以下の要員情報を送ってきている会社を全件抽出する
対象: sessales / matsuno / okamoto 全受信箱
"""

import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import email
import imaplib
import os
import re
from collections import defaultdict
from email.header import decode_header

from dotenv import load_dotenv

ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", ".env")
load_dotenv(ENV_PATH)

ACCOUNTS = {
    "sessales": {
        "host": os.getenv("OUTLOOK_IMAP_SERVER", "outlook.office365.com"),
        "port": int(os.getenv("OUTLOOK_IMAP_PORT", 993)),
        "user": os.getenv("SESSALES_EMAIL", "sessales@terra-ltd.co.jp"),
        "pass": os.getenv("SESSALES_PASSWORD") or os.getenv("SESSALES_MAIL_PASSWORD"),
    },
    "matsuno": {
        "host": os.getenv("OUTLOOK_IMAP_SERVER", "outlook.office365.com"),
        "port": int(os.getenv("OUTLOOK_IMAP_PORT", 993)),
        "user": os.getenv("MATSUNO_EMAIL", "r-matsuno@terra-ltd.co.jp"),
        "pass": os.getenv("MATSUNO_PASSWORD"),
    },
    "okamoto": {
        "host": os.getenv("OUTLOOK_IMAP_SERVER", "outlook.office365.com"),
        "port": int(os.getenv("OUTLOOK_IMAP_PORT", 993)),
        "user": os.getenv("OKAMOTO_EMAIL", "r-okamoto@terra-ltd.co.jp"),
        "pass": os.getenv("OKAMOTO_PASSWORD"),
    },
}

# デバッグ: パスワード確認（マスク表示）
for k, v in ACCOUNTS.items():
    pw = v["pass"]
    print(f"[ACCOUNT] {k}: {v['user']} / pass={'***' if pw else 'MISSING'} / host={v['host']}")

PRICE_PATTERNS = [
    r"単価\s*[：:＝=]?\s*(\d{2,3}(?:\.\d)?)\s*万",
    r"(\d{2,3}(?:\.\d)?)\s*万円",
    r"(\d{2,3}(?:\.\d)?)\s*万/月",
    r"(\d{2,3}(?:\.\d)?)\s*万\s*/\s*月",
    r"単価\s*[：:＝=]?\s*(\d{3},\d{3})",
    r"(\d{3},\d{3})\s*円",
    r"単価\s*[：:＝=]?\s*([1-9]\d{5})",
    r"([1-9]\d{5})\s*円",
]


def decode_str(s):
    if s is None:
        return ""
    parts = decode_header(s)
    result = []
    for part, enc in parts:
        if isinstance(part, bytes):
            result.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            result.append(str(part))
    return "".join(result)


def get_body(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition", ""))
            if ct in ("text/plain", "text/html") and "attachment" not in cd:
                charset = part.get_content_charset() or "utf-8"
                raw = part.get_payload(decode=True)
                if raw:
                    body += raw.decode(charset, errors="replace") + "\n"
    else:
        charset = msg.get_content_charset() or "utf-8"
        raw = msg.get_payload(decode=True)
        if raw:
            body = raw.decode(charset, errors="replace")
    # HTMLタグ除去
    body = re.sub(r"<[^>]+>", "", body)
    return body


def extract_price(text):
    prices = []
    for pat in PRICE_PATTERNS:
        for m in re.finditer(pat, text):
            val_str = m.group(1).replace(",", "")
            try:
                val = float(val_str)
                if val >= 100000:  # 100000円以上 → 万に変換
                    val /= 10000
                elif val >= 1000:  # 1000以上は円表記の可能性
                    val /= 10000
                prices.append(val)
            except:
                pass
    return prices


def extract_signature(body):
    """本文末尾から署名ブロックを取得"""
    # 区切り線を探す
    seps = [r"[-─━]{3,}", r"={3,}", r"_{3,}", r"/{3,}", r"\*{3,}"]
    best_pos = len(body)
    for sep in seps:
        for m in re.finditer(sep, body):
            if m.start() > len(body) * 0.5:  # 後半にある区切り
                if m.start() < best_pos:
                    best_pos = m.start()

    sig = body[best_pos:].strip()
    if len(sig) < 20:  # 短すぎる → 末尾を取る
        lines = body.strip().split("\n")
        sig = "\n".join(lines[-20:]).strip()
    return sig[:600]


def is_candidate_mail(subject, body):
    keywords = [
        "要員",
        "エンジニア",
        "SE",
        "PG",
        "PM",
        "スキルシート",
        "単価",
        "稼働",
        "経験年数",
        "ご紹介",
        "人材",
        "フリーランス",
        "候補者",
        "Java",
        "Python",
        "PHP",
        "AWS",
        "Azure",
        "インフラ",
        "DB",
        "SQL",
        "フロントエンド",
        "バックエンド",
        "クラウド",
        "テスト",
        "開発",
    ]
    combined = subject + "\n" + body[:500]
    return any(kw in combined for kw in keywords)


sender_data = defaultdict(
    lambda: {
        "name": "",
        "min_price": 999.0,
        "max_price": 0.0,
        "count": 0,
        "signature": "",
        "subjects": [],
        "accounts": set(),
    }
)

total_checked = 0
total_candidate = 0

for acct_name, acct in ACCOUNTS.items():
    if not acct["pass"]:
        print(f"[SKIP] {acct_name}: パスワード未設定")
        continue

    print(f"\n[INFO] {acct_name} ({acct['user']}) 接続中...")
    try:
        mail = imaplib.IMAP4_SSL(acct["host"], acct["port"])
        mail.login(acct["user"], acct["pass"])

        # 利用可能なフォルダ確認
        _, folders = mail.list()
        print("[INFO] ログイン成功。フォルダ検索中...")

        mail.select("INBOX")
        _, msgs = mail.search(None, "ALL")
        msg_ids = msgs[0].split() if msgs[0] else []
        print(f"[INFO] INBOX: {len(msg_ids)}件")

        # 大量の場合は直近3000件に絞る
        if len(msg_ids) > 3000:
            msg_ids = msg_ids[-3000:]

        checked_this = 0
        for mid in msg_ids:
            try:
                _, data = mail.fetch(mid, "(RFC822)")
                if not data or not data[0]:
                    continue
                raw = data[0][1]
                msg = email.message_from_bytes(raw)

                subject = decode_str(msg.get("Subject", ""))
                from_raw = decode_str(msg.get("From", ""))
                body = get_body(msg)
                total_checked += 1
                checked_this += 1

                if checked_this % 200 == 0:
                    print(f"  ... {checked_this}/{len(msg_ids)} 処理中")

                if not is_candidate_mail(subject, body):
                    continue

                prices = extract_price(subject + "\n" + body[:2000])
                low_prices = [p for p in prices if 0 < p <= 40]

                if not low_prices:
                    continue

                total_candidate += 1
                min_p = min(low_prices)
                max_p = max(low_prices)

                # 送信者正規化
                addr_m = re.search(r"<(.+?)>", from_raw)
                from_addr = addr_m.group(1).lower().strip() if addr_m else from_raw.lower().strip()
                name_m = re.match(r"^(.+?)\s*<", from_raw)
                from_name = name_m.group(1).strip().strip('"') if name_m else from_addr.split("@")[0]

                sd = sender_data[from_addr]
                if not sd["name"] or len(from_name) > len(sd["name"]):
                    sd["name"] = from_name
                sd["count"] += 1
                sd["min_price"] = min(sd["min_price"], min_p)
                sd["max_price"] = max(sd["max_price"], max_p)
                sd["accounts"].add(acct_name)
                if subject not in sd["subjects"]:
                    sd["subjects"].append(subject)
                if not sd["signature"]:
                    sd["signature"] = extract_signature(body)

            except Exception:
                pass

        mail.logout()
        print(f"[INFO] {acct_name} 完了: {checked_this}件チェック")

    except Exception as e:
        print(f"[ERROR] {acct_name}: {type(e).__name__}: {e}")

# ========== 結果出力 ==========
print(f"\n{'=' * 60}")
print(f"完了: チェック{total_checked}件 / 40万以下要員メール{total_candidate}件 / {len(sender_data)}社")
print(f"{'=' * 60}")

sorted_senders = sorted(sender_data.items(), key=lambda x: x[1]["count"], reverse=True)

OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "low_price_senders_result.txt")
lines_out = [f"40万以下の要員情報送信会社一覧\n総計 {len(sorted_senders)}社\nチェックメール数: {total_checked}件\n\n"]

for i, (addr, sd) in enumerate(sorted_senders, 1):
    block = f"""No.{i}
【送信元名】{sd["name"]}
【メアド】{addr}
【送信件数】{sd["count"]}件
【受信アカウント】{", ".join(sd["accounts"])}
【単価帯】{sd["min_price"]:.0f}万 〜 {sd["max_price"]:.0f}万
【件名サンプル】
"""
    for s in sd["subjects"][:3]:
        block += f"  ・{s}\n"
    block += f"【署名】\n{sd['signature']}\n{'━' * 55}\n"
    lines_out.append(block)
    print(block)

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(lines_out))

print(f"\n[保存] {OUTPUT_PATH}")
