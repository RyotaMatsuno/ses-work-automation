"""
新モデル実機テスト(修正版): max_completion_tokens使用
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
]

print("=" * 60)
print("新モデル実機テスト(修正版)")
print("=" * 60)

available = []

for model in models_to_test:
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Reply with just OK"}],
            max_completion_tokens=50,
        )
        result = response.choices[0].message.content
        usage = response.usage
        print(f"✅ {model}: '{result}' (in={usage.prompt_tokens}, out={usage.completion_tokens})")
        available.append(model)
    except Exception as e:
        err = str(e)[:150]
        print(f"❌ {model}: {err}")

# gpt-5.3-codexは別エンドポイント
print("\ngpt-5.3-codex (Completions API):")
try:
    response = client.completions.create(
        model="gpt-5.3-codex",
        prompt="# Function to add two numbers\ndef add(a, b):\n    ",
        max_tokens=30,
    )
    print("✅ gpt-5.3-codex: 動作OK")
    print(f"   出力: {response.choices[0].text[:100]}")
    available.append("gpt-5.3-codex")
except Exception as e:
    print(f"❌ gpt-5.3-codex: {str(e)[:200]}")

# Responses APIも試す(o3系の新仕様かも)
print("\nResponses APIテスト(gpt-5.3-codex):")
try:
    response = client.responses.create(
        model="gpt-5.3-codex",
        input="Write a Python function to add two numbers",
    )
    print("✅ gpt-5.3-codex via responses: OK")
    print(f"   出力: {response.output_text[:200] if hasattr(response, 'output_text') else str(response)[:200]}")
except Exception as e:
    print(f"❌ responses API: {str(e)[:200]}")

print()
print("=" * 60)
print(f"利用可能: {available}")
print("=" * 60)
