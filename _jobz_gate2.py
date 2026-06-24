import os
import sys
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES = os.getcwd()
env_path = Path(SES) / "config" / ".env"
config = {}
with open(env_path, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            config[k.strip()] = v.strip()

OPENAI_KEY = config.get("OPENAI_API_KEY", "")

# 修正コードを読む
gc_py = Path(SES) / "gate_checker" / "gate_check.py"
with open(gc_py, encoding="utf-8") as f:
    lines = f.readlines()

# needs_human_review + resolve_human_review の該当行を抽出
relevant = []
capture = False
for i, line in enumerate(lines, 1):
    if "def needs_human_review" in line or "def resolve_human_review" in line:
        capture = True
    if capture:
        relevant.append(f"L{i}: {line.rstrip()}")
    if (
        capture
        and i > 5
        and line.strip().startswith("def ")
        and "needs_human_review" not in line
        and "resolve_human_review" not in line
    ):
        capture = False

# run_gate_check の human_review 周辺
for i, line in enumerate(lines, 1):
    if "resolve_human_review" in line and "def" not in line:
        ctx = lines[max(0, i - 3) : min(len(lines), i + 3)]
        for j, cl in enumerate(ctx, i - 2):
            relevant.append(f"L{j}: {cl.rstrip()}")

# テストコード
test_path = Path(SES) / "gate_checker" / "tests" / "test_human_review_override.py"
with open(test_path, encoding="utf-8") as f:
    test_code = f.read()

code_snippet = "\n".join(relevant)

review_request = f"""
【ゲート②：コードレビュー依頼】
システム: gate_checker/gate_check.py
修正内容: needs_human_review 誤検知抑制ロジック追加

■ 修正の背景
verdict==OK かつ GPTが HUMAN_REVIEW: NO と自己判定した場合でも、
レビュー本文中の「請求」「単価」等のキーワードに層2（類義語マッチ）が反応し
needs_human_review=True になる誤検知が発生していた。

■ 修正コード
{code_snippet}

■ テストコード（5件全通過確認済み）
{test_code}

■ レビュー観点
1. resolve_human_review のロジックに抜け・矛盾はないか
2. NG + HUMAN_REVIEW: NO（壁打ちパス）が意図通り動くか
3. 条件付きGO の verdict=="OK" マッピングは parse_judgment の仕様と整合しているか
4. 既存の needs_human_review の動作を壊していないか
5. このまま本番運用して問題ないか

【判定: GO】または【判定: NG】で返してください。
"""

headers = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}
payload = {
    "model": "gpt-4o",
    "messages": [
        {
            "role": "system",
            "content": "あなたはPythonコードレビューの専門家です。提示されたコードと修正内容を正確に分析し、GO/NGで判定してください。日本語で回答してください。",
        },
        {"role": "user", "content": review_request},
    ],
    "max_tokens": 1000,
    "temperature": 0,
}

print("■ GPT-4o ゲート② 送信中...")
r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=60)
r.raise_for_status()
result = r.json()
review = result["choices"][0]["message"]["content"]
print("\n■ GPT-4o ゲート② レビュー結果:")
print(review)
print(f"\n■ トークン: {result['usage']}")
