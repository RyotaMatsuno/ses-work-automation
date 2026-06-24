#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Anthropic Admin API でusage取得試行 (Admin Keyなければエラー)"""

import os
import sys

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

load_dotenv("C:/Users/ma_py/OneDrive/デスクトップ/ses_work/config/.env")

API_KEY = os.environ["ANTHROPIC_API_KEY"]
print(f"[INFO] Key prefix: {API_KEY[:15]}...")
# admin keyは sk-ant-admin-... / inference keyは sk-ant-api03-... または sk-ant-...

# Admin API: organization-level usage report (2024リリース)
URLS = [
    "https://api.anthropic.com/v1/organizations/usage_report/messages?starting_at=2026-06-01&ending_at=2026-06-16",
    "https://api.anthropic.com/v1/organizations/cost_report?starting_at=2026-06-01&ending_at=2026-06-16",
]

headers = {
    "x-api-key": API_KEY,
    "anthropic-version": "2023-06-01",
    "Content-Type": "application/json",
}

for url in URLS:
    print(f"\n===== {url} =====")
    try:
        r = requests.get(url, headers=headers, timeout=20)
        print(f"Status: {r.status_code}")
        print(r.text[:1500])
    except Exception as e:
        print(f"Error: {e}")
