# -*- coding: utf-8 -*-
"""
pipeline_notify_fix.py
3ファイルをまとめて修正するパッチスクリプト
"""

import io
import os
import shutil
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
PIPELINE = os.path.join(BASE, r"mail_pipeline\mail_pipeline.py")
MATCHING = os.path.join(BASE, r"matching_v2\matching_v2.py")
NOTIFY = os.path.join(BASE, r"matching_v2\notify_line.py")

errors = []


def read(path):
    return open(path, encoding="utf-8").read()


def write(path, content):
    open(path, "w", encoding="utf-8").write(content)


def backup(path):
    bak = path + ".bak_pfix"
    if not os.path.exists(bak):
        shutil.copy2(path, bak)


def patch(path, old, new, label):
    content = read(path)
    if old in content:
        write(path, content.replace(old, new, 1))
        print(f"  [OK] {label}")
        return True
    else:
        print(f"  [SKIP] {label} - pattern not found")
        errors.append(f"{label}: pattern not found in {os.path.basename(path)}")
        return False


# ==========================================
# 1. mail_pipeline.py バックアップ＆修正
# ==========================================
print("=== Fix 1: mail_pipeline.py ===")
backup(PIPELINE)

# 1-1. FETCH_LIMIT / PROCESS_LIMIT
patch(
    PIPELINE,
    "FETCH_LIMIT = 50\nPROCESS_LIMIT = 20",
    "FETCH_LIMIT = 500\nPROCESS_LIMIT = 500",
    "FETCH_LIMIT=500, PROCESS_LIMIT=500",
)

# 1-2. IMAP search を SINCE当日 + ALL fallback に変更
old_search = """    status, messages = mail.search(None, "ALL")
    if status != "OK" or not messages[0]:
        log("対象メールなし")
        mail.logout()
        return []

    all_ids = messages[0].split()
    log(f"全メール: {len(all_ids)}件 → 直近{limit}件を処理対象")
    target_ids = list(reversed(all_ids[-limit:]))"""

new_search = """    today_str = datetime.now().strftime("%d-%b-%Y")
    status, messages = mail.search(None, f"SINCE {today_str}")
    if status != "OK" or not messages[0]:
        status, messages = mail.search(None, "ALL")
    if status != "OK" or not messages[0]:
        log("対象メールなし")
        mail.logout()
        return []

    all_ids = messages[0].split()
    log(f"全メール: {len(all_ids)}件 → 直近{limit}件を処理対象")
    target_ids = list(reversed(all_ids[-limit:]))"""

patch(PIPELINE, old_search, new_search, "IMAP SINCE today search")

# ==========================================
# 2. matching_v2.py バックアップ＆修正
# ==========================================
print("\n=== Fix 2: matching_v2.py ===")
backup(MATCHING)
m2 = read(MATCHING)

# プロジェクトにraw_bodyを追加する箇所を探す
# Notionからproject情報を構築している部分を確認
for i, line in enumerate(m2.splitlines()):
    if ("案件詳細" in line or "案件名" in line or "project_name" in line) and "props" in line:
        print(f"  候補行 {i + 1}: {line.strip()[:80]}")

# engineerにraw_bodyを追加する箇所
for i, line in enumerate(m2.splitlines()):
    if ("備考" in line or "note" in line.lower()) and "props" in line:
        print(f"  eng候補行 {i + 1}: {line.strip()[:80]}")
