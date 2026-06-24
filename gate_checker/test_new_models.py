"""
新モデル実機テスト: gpt-5.5 / gpt-5.4 / gpt-5.4-mini / gpt-5.3-codex が呼べるか
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

models_to_test = [
    "gpt-5.5",
    "gpt-5.4",
    "gpt-5.4-mini",
    "gpt-5.4-nano",
    "gpt-5.3-codex",
]

print("=" * 60)
print("新モデル実機テスト")
print("=" * 60)

available = []
unavailable = []

for model in models_to_test:
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Reply with just OK"}],
            max_tokens=10,
        )
        result = response.choices[0].message.content
        print(f"✅ {model}: 動作OK -> {result}")
        available.append(model)
    except Exception as e:
        err = str(e)[:200]
        print(f"❌ {model}: {err}")
        unavailable.append((model, err))

print()
print("=" * 60)
print(f"利用可能: {len(available)}/{len(models_to_test)}")
print(f"利用可能モデル: {available}")
print("=" * 60)

# o3系も確認(旧世代だが動くか)
print("\n旧モデル参考確認:")
old_models = ["o3", "o3-mini", "gpt-4o", "gpt-4o-mini"]
for model in old_models:
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Reply with just OK"}],
            max_tokens=10,
        )
        print(f"  {model}: 動作OK (旧世代だが現役)")
    except Exception as e:
        print(f"  {model}: NG ({str(e)[:100]})")
