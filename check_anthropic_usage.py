# -*- coding: utf-8 -*-
# Anthropic Admin APIで実際の使用量・コストを確認
import sys
from datetime import datetime, timedelta, timezone

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import dotenv_values

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
API_KEY = env.get("ANTHROPIC_API_KEY", "")
ADMIN_KEY = env.get("ANTHROPIC_ADMIN_KEY", "")

# Admin keyがあるか確認
print("ANTHROPIC_ADMIN_KEY設定:", "あり" if ADMIN_KEY else "なし")
print("ANTHROPIC_API_KEY設定:", "あり" if API_KEY else "なし")

# Usage APIを試す（Admin keyが必要）
if ADMIN_KEY:
    headers = {"x-api-key": ADMIN_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    # コスト取得
    JST = timezone(timedelta(hours=9))
    today = datetime.now(JST).strftime("%Y-%m-%d")
    try:
        r = requests.get(
            f"https://api.anthropic.com/v1/organizations/cost_report?starting_at={today}T00:00:00Z",
            headers=headers,
            timeout=15,
        )
        print(f"\nCost report: {r.status_code}")
        print(r.text[:1000])
    except Exception as e:
        print(f"エラー: {e}")
else:
    print("\nAdmin keyがないため Usage API は使えません")

# .envの全キーをチェック（コスト関連設定）
print("\n=== .env コスト関連設定 ===")
for k, v in env.items():
    if any(x in k.upper() for x in ["COST", "LIMIT", "BUDGET", "SPEND", "CHARGE", "BILLING"]):
        print(f"  {k}={v}")
