# -*- coding: utf-8 -*-
"""
RontenB info gathering:
1. Anthropic pricing page scrape (Sonnet 4.6 / Opus 4.7 / 4.8 unit price)
2. Cursor docs scrape (multi-provider config)
"""

import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import re
import urllib.request

urls_to_check = [
    "https://www.anthropic.com/pricing",
    "https://docs.anthropic.com/en/docs/about-claude/models/overview",
    "https://docs.cursor.com/account/pricing",
    "https://docs.cursor.com/settings/models",
]

for url in urls_to_check:
    print("=" * 70)
    print(f"URL: {url}")
    print("=" * 70)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            body = r.read().decode("utf-8", errors="replace")
        # キーワード検出
        keywords_pricing = [
            "sonnet",
            "opus",
            "haiku",
            "$3",
            "$15",
            "$5",
            "$75",
            "claude-sonnet-4-6",
            "claude-opus-4",
            "4.7",
            "4.8",
        ]
        keywords_cursor = ["api key", "custom model", "provider", "openai", "anthropic", "azure"]
        kw_list = keywords_cursor if "cursor" in url else keywords_pricing
        print(f"body_len={len(body)}")
        for kw in kw_list:
            count = body.lower().count(kw.lower())
            print(f"  '{kw}': {count} hits")
        # 価格関連の行を抽出(数字とドルが近接する箇所)
        price_matches = re.findall(r".{0,80}\$\d+[\.\d]*.{0,80}", body[:50000])
        if price_matches:
            print("\n  Price-related snippets (first 5):")
            for m in price_matches[:5]:
                m_clean = re.sub(r"<[^>]+>", "", m).strip()[:150]
                if m_clean:
                    print(f"    - {m_clean}")
    except Exception as e:
        print(f"  ERROR: {str(e)[:200]}")
    print()
