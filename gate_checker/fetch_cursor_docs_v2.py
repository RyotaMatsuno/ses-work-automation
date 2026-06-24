#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Cursor pricing詳細・モデル一覧"""

import re
import sys
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

URLS = [
    ("pricing", "https://www.cursor.com/pricing"),
    ("plans-faq", "https://docs.cursor.com/en/account/plans-and-usage"),
    ("models", "https://docs.cursor.com/en/models"),
    ("usage", "https://docs.cursor.com/en/account/usage"),
    ("api-keys", "https://docs.cursor.com/en/account/api-keys"),
    ("changelog", "https://www.cursor.com/changelog"),
]

headers = {"User-Agent": "Mozilla/5.0"}

for label, url in URLS:
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as r:
            body = r.read().decode("utf-8", errors="replace")
        raw_len = len(body)
        body = re.sub(r"<script.*?</script>", "", body, flags=re.S)
        body = re.sub(r"<style.*?</style>", "", body, flags=re.S)
        body = re.sub(r"<[^>]+>", " ", body)
        body = re.sub(r"\s+", " ", body)
        print(f"\n===== [{label}] {url}  (raw={raw_len}, text={len(body)}) =====")
        # 全文表示（5000文字まで）
        print(body[:5000])
    except urllib.error.HTTPError as e:
        print(f"\n===== [{label}] {url} =====\nHTTPError: {e.code}")
    except Exception as e:
        print(f"\n===== [{label}] {url} =====\nError: {e}")
