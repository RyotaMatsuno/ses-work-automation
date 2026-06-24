#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Cursor公式ドキュメント取得（Pro plan仕様確認用）"""

import re
import sys
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

URLS = [
    "https://docs.cursor.com/account/plans-and-usage",
    "https://docs.cursor.com/account/plans",
    "https://docs.cursor.com/account/pricing",
    "https://www.cursor.com/pricing",
    "https://cursor.com/pricing",
    "https://docs.cursor.com/models/models",
    "https://docs.cursor.com/models",
]

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

for url in URLS:
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as r:
            body = r.read().decode("utf-8", errors="replace")
        # HTMLからscript/styleを除去してテキスト化
        body = re.sub(r"<script.*?</script>", "", body, flags=re.S)
        body = re.sub(r"<style.*?</style>", "", body, flags=re.S)
        body = re.sub(r"<[^>]+>", " ", body)
        body = re.sub(r"\s+", " ", body)
        # キーワード周辺だけ抽出
        keywords = [
            "Pro",
            "fast",
            "slow",
            "$20",
            "limit",
            "credit",
            "request",
            "Sonnet",
            "codex",
            "GPT-5",
            "Claude",
            "model",
        ]
        snippets = []
        for kw in keywords:
            for m in re.finditer(re.escape(kw), body, flags=re.IGNORECASE):
                s = max(0, m.start() - 80)
                e = min(len(body), m.end() + 200)
                snippets.append(body[s:e])
        # 重複削減
        snippets = list(dict.fromkeys(snippets))[:10]
        print(f"\n===== {url} =====")
        print(f"Status: OK  Body length: {len(body)}")
        for sn in snippets:
            print("  -", sn.strip()[:300])
    except urllib.error.HTTPError as e:
        print(f"\n===== {url} =====\nHTTPError: {e.code}")
    except Exception as e:
        print(f"\n===== {url} =====\nError: {e}")
