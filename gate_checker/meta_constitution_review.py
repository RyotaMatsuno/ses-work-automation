"""
メタ壁打ち: 行動憲法書換え案の評価
「すべての判断にGPT壁打ちを必須化する」というルール変更自体の妥当性を検証
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

PROPOSAL = """
# 行動憲法書換え案

## 背景
- 松野CEOはClaude(ジョブズ)を経営参謀として使用
- ジョブズ独断で進めるとGPT壁打ちで見落としが頻発(過去事例多数)
- 松野は「すべての判断はGPT壁打ち必須」と要求

## 新ルール案
1. ジョブズが新しいことを進める際、必ずGPT壁打ちを実施
2. 複数モデル(o3-mini / o3 / gpt-4o)で多視点レビュー
3. GPT・ジョブズ双方が問題なしと判断 → 松野確認なしで進めてOK
4. どちらか問題あり → 松野に判断を仰ぐ
5. 壁打ちログは全件Notion or ファイルに保存(松野が後から見える)

## 想定される運用負荷
- 1判断あたりGPT 2〜3ラウンド(現実例: 7ラウンド$0.117/件)
- 1日5判断とすると月コスト$15〜25
- 各判断で松野が待つ時間: 1〜3分程度

## GPTへの問い
1. このルールは合理的か? 過剰か?
2. 「新しいこと」の定義をどう線引きするか?(全部壁打ちすると過剰)
3. 「壁打ち不要」と判定できるケースはあるか?(例: 既存パターンの繰返し)
4. ジョブズの「独断暴走癖」をどう抑制するか
5. 松野確認ステップを完全に省くことのリスク
6. 壁打ち結果でGPTとジョブズが共謀する(両方とも甘い判断する)リスクへの対策
7. 「最終チェック必須」のチェック粒度はどこまで細かくすべきか
8. このメタルール自体のアップデート手順
"""

PROMPT = f"""
あなたはAI運用設計の専門家。以下の経営判断ルール案を厳しく評価せよ。

{PROPOSAL}

【出力形式】
## 結論(GO/HOLD/NG)
## このルールの強み
## 致命的弱点
## 「新しいこと」の定義線引き
## 壁打ち省略可能なケース
## 共謀リスクへの対策
## 最終推奨ルール(具体的に書き直す)
## 運用開始前に絶対やるべきこと
"""

print("=" * 60)
print("メタ壁打ち: 行動憲法書換え評価 (o3)")
print("=" * 60)

response = client.chat.completions.create(
    model="o3",
    messages=[{"role": "user", "content": PROMPT}],
    reasoning_effort="high",
)

result = response.choices[0].message.content
print(result)
print()
cost = response.usage.prompt_tokens * 2 / 1_000_000 + response.usage.completion_tokens * 8 / 1_000_000
print(f"コスト: ${cost:.4f}")
