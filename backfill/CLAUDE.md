# CLAUDE.md - backfill_engineers
# Rules for Codex: read this before writing any code.

## Task Overview
Backfill script for Notion Engineer DB.
Target: records where イニシャル / 所属メール / 所属担当者名 are all empty.
Source: 備考（LINEメモ）field which contains a line like "送信元: ..."

## Absolute Rules
- NEVER delete or overwrite existing non-empty field values
- Only update fields that are currently empty
- Use dotenv_values('config/.env') to load credentials
- NOTION_API_KEY is the key name in .env
- Notion-Version header: 2022-06-28
- Engineer DB ID: 343450ff-37c0-819d-8769-fb0a8a4ceeb1
- All prints must be ASCII or use encode/decode for Japanese (cp932 env)
- Add 0.3s sleep between Notion PATCH calls to avoid rate limit
- Script path: ses_work/backfill_engineers.py

## Field Mapping
- イニシャル (rich_text): derive from 名前 field - take first char of each space-separated token
  - "川村 俊之" -> "K.T" (romaji initials using first char logic - see SPEC)
  - If 名前 already looks like initials (e.g. "K.I", "OT", "UT"), use as-is
  - If 名前 is a skill-sheet code (e.g. "174BZ06"), skip イニシャル generation
- 所属メール (email): extract from 送信元 line in 備考（LINEメモ）
- 所属担当者名 (rich_text): extract person name from 送信元 line if present

## Do NOT touch
- 名前, スキル, 単価（万円）, 稼働可能日, 稼働状況, 担当者, 入力元
- Any field that already has a value
