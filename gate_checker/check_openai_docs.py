# -*- coding: utf-8 -*-
"""
OpenAI公式pricing/modelsページの記載を取得してジョブズ側で型番を確認。
"""

import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import urllib.request

urls = [
    "https://platform.openai.com/docs/models",
    "https://openai.com/api/pricing/",
]

for u in urls:
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            body = r.read().decode("utf-8", errors="replace")
        # gpt-5.5系のキーワードを抽出
        hits = []
        for kw in ["gpt-5.5", "gpt-5.4", "gpt-5.3-codex", "gpt-5.4-mini", "gpt-5.4-nano"]:
            count = body.count(kw)
            hits.append(f"{kw}={count}")
        print(f"URL: {u}")
        print(f"  status=OK, body_len={len(body)}")
        print(f"  keyword counts: {', '.join(hits)}")
    except Exception as e:
        print(f"URL: {u}")
        print(f"  ERROR: {str(e)[:200]}")
    print()
