# -*- coding: utf-8 -*-
import sys
import time

import requests
from dotenv import dotenv_values

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
KEY = env.get("GEMINI_API_KEY", "")
URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={KEY}"

Qs = [
    {
        "id": "Q1",
        "q": (
            "Claude AIの記憶なし・ルール崩壊を防ぐプロンプト設計について。"
            "現状: 【毎回必読】行動憲法30行 / 【詰まったら】ハマりパターン辞書 / 【参照用】CEO指示書v10。"
            "以下の4点について具体的な改善提案を200字以内で。"
            "①チャット間記憶補完(PJファイル/userMemory活用) "
            "②毎チャット確実に読ませる構成 "
            "③ハマりパターン辞書の最適構造 "
            "④引き継ぎプロトコル改善余地"
        ),
    },
    {
        "id": "Q2",
        "q": (
            "AI経営参謀の行動憲法を30行に収める優先順位付け。"
            "カテゴリ: ①行動ルール ②事業コンテキスト(契約/粗利/ID) ③技術制約(jobz/Notion/freee) ④エスカレーション条件 ⑤モデル選択ルール。"
            "30行の配分案と、別ファイルに出すべき情報を100字以内で具体的に示してください。"
        ),
    },
]

for q in Qs:
    print(f"\n{'=' * 60}")
    print(f"【Gemini {q['id']}】")
    payload = {
        "contents": [{"parts": [{"text": q["q"]}]}],
        "generationConfig": {"maxOutputTokens": 1024, "temperature": 0},
    }
    for attempt in range(3):
        r = requests.post(URL, json=payload, timeout=60)
        if r.status_code == 429:
            time.sleep(20 * (attempt + 1))
            continue
        r.raise_for_status()
        print(r.json()["candidates"][0]["content"]["parts"][0]["text"])
        break
    time.sleep(10)
