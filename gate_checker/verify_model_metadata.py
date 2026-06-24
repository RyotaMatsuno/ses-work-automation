# -*- coding: utf-8 -*-
"""
APIが返すmodelフィールドが本物の型番か検証する。
alias/redirectされていないかを response.model で確認。
"""

import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import os
from pathlib import Path

from openai import OpenAI

env_path = Path("config/.env")
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip().strip('"')

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

print("=" * 60)
print("モデルメタデータ検証(エイリアス検出)")
print("=" * 60)

models = ["gpt-5.5", "gpt-5.4", "gpt-5.4-mini", "gpt-5.4-nano", "gpt-4o", "gpt-4o-mini"]

for m in models:
    try:
        r = client.chat.completions.create(
            model=m,
            messages=[{"role": "user", "content": "x"}],
            max_completion_tokens=5,
        )
        print(f"requested={m:20s} -> response.model={r.model}")
    except Exception as e:
        print(f"requested={m:20s} -> ERROR: {str(e)[:120]}")

print("\n" + "=" * 60)
print("models.list() でアカウントが見ているモデル一覧(gpt-5系のみ)")
print("=" * 60)
try:
    ml = client.models.list()
    gpt5 = sorted([m.id for m in ml.data if "gpt-5" in m.id or "gpt-4o" in m.id])
    for mid in gpt5:
        print(f"  {mid}")
except Exception as e:
    print(f"ERROR: {e}")
