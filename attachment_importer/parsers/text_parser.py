# -*- coding: utf-8 -*-
"""テキストサマリーから人員情報を構造化抽出する。"""

import json, os, re, sys
from datetime import date
from typing import Any
import anthropic

DELIMITER_PATTERNS = [r'-{10,}', r'ー{5,}', r'━{5,}', r'={10,}', r'_{10,}', r'\*{10,}']
DELIMITER_RE = re.compile('|'.join(DELIMITER_PATTERNS))
NAME_KEYWORDS = ['氏名', '名前', '■名前', '【名前】', '【氏名】', '■氏名', 'お名前']
INITIAL_RE = re.compile(r'[A-Z]\.[A-Z]')


def split_into_blocks(text: str) -> list:
    parts = DELIMITER_RE.split(text)
    blocks = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        has_name = any(kw in part for kw in NAME_KEYWORDS)
        has_initial = bool(INITIAL_RE.search(part))
        if has_name or has_initial:
            blocks.append(part)
    return blocks


def extract_person_from_block(block: str, client, today: str) -> dict:
    prompt = f"""以下の人員情報テキストから構造化データを抽出してください。
不明な項目はnullにしてください。JSONのみ返してください（マークダウン不要）。
今日の日付: {today}

{block}

返すJSON:
{{
  "name": "氏名",
  "age": null,
  "gender": null,
  "nearest_station": null,
  "affiliation": null,
  "price": null,
  "available_date": null,
  "skills_list": [],
  "experience_years": null,
  "contact_email": null,
  "contact_phone": null,
  "remote_preference": null,
  "raw_text": "原文全体"
}}"""
    for attempt in range(3):
        try:
            msg = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = msg.content[0].text.strip()
            raw = re.sub(r'^```[a-z]*\n?', '', raw)
            raw = re.sub(r'\n?```$', '', raw)
            return json.loads(raw)
        except Exception as e:
            if attempt == 2:
                return {"name": None, "raw_text": block, "_parse_error": str(e)}
    return {"name": None, "raw_text": block}


def parse_text(text: str, api_key: str = None) -> list:
    key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    client = anthropic.Anthropic(api_key=key)
    today = date.today().isoformat()
    blocks = split_into_blocks(text)
    if not blocks:
        blocks = [text.strip()]
    results = []
    for block in blocks:
        person = extract_person_from_block(block, client, today)
        if person.get("name") or person.get("raw_text"):
            results.append(person)
    return results
