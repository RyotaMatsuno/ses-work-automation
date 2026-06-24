# -*- coding: utf-8 -*-
"""
Anthropic models overview から Sonnet 4.6 / Opus 4.7 / 4.8 の単価を抽出
"""

import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import re
import urllib.request

url = "https://docs.anthropic.com/en/docs/about-claude/models/overview"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=15) as r:
    body = r.read().decode("utf-8", errors="replace")

# HTMLタグ除去
text = re.sub(r"<[^>]+>", " ", body)
text = re.sub(r"\s+", " ", text)

# 価格関連の文脈を抽出
patterns = [
    r".{0,150}sonnet.{0,300}",
    r".{0,150}opus.{0,300}",
    r".{0,150}haiku.{0,300}",
    r".{0,80}claude-sonnet-4-6.{0,200}",
    r".{0,80}claude-opus-4.{0,200}",
    r".{0,80}claude-opus-4-7.{0,200}",
    r".{0,80}claude-opus-4-8.{0,200}",
    r".{0,30}\$\d+.{0,30}/.{0,30}M.{0,30}tokens.{0,80}",
    r".{0,80}Input.{0,30}\$.{0,80}",
    r".{0,80}Output.{0,30}\$.{0,80}",
]

seen = set()
print("=" * 70)
print("Anthropic models overview - price extraction")
print("=" * 70)

for pat in patterns:
    matches = re.findall(pat, text, re.IGNORECASE)
    for m in matches[:10]:
        snippet = m.strip()[:400]
        # 重複除去
        key = snippet[:80]
        if key in seen:
            continue
        seen.add(key)
        # 価格・モデル名が含まれてるものだけ
        if any(k in snippet.lower() for k in ["$", "sonnet 4", "opus 4", "haiku 4", "claude-"]):
            print("\n--- match ---")
            print(snippet)
