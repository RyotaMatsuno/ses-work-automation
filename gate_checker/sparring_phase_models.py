"""
GPT-4oに「フェーズ別モデル割り振り案」を壁打ちさせる単発スクリプト
2026-06-16 ジョブズが松野の指示で実行
"""

import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import os
from pathlib import Path

from openai import OpenAI

# .env読込
env_path = Path("config/.env")
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip().strip('"')

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

CONTEXT = """
事業: SES営業自動化システム(2名体制・松野CEO+岡本パートナー)
体制: ジョブズ(Claude Opus 4.8 = 経営参謀) + Cursor(実装) + gate_checker(GPT-4oレビュー)
規模想定: 1日5タスク × 1タスク6工程 × 各工程平均8往復 = 1日240回API呼出
現状: gate_checker全フェーズ一律 gpt-4o 使用 → 月$80-120

【ジョブズの提案】フェーズ別モデル切替:
- research(調査)       → gpt-4o-mini   (単純調査・安い)
- requirements(要件)   → gpt-4o-mini   (形式チェック)
- design(設計)         → o3-mini       (推論必要)
- pre_impl(実装前確認) → gpt-4o-mini
- implementation(コードレビュー) → gpt-4o (高精度)
- test(テスト観点)     → gpt-4o-mini
- final_gate(最終判定) → o3            (最重要判断)

期待効果: 精度向上(o3導入) + コスト半減(月$30-50)

【ジョブズが見落としてる可能性】
- miniの精度落ちでバグ見逃しリスク
- o3の応答時間遅延でフロー詰まる
- フェーズ境界の判定ミス
- 1往復で8回壁打ちは過剰か不足か
"""

PROMPT = f"""
あなたはAIシステム設計の専門家。以下のジョブズ案を厳しめにレビューしてください。

{CONTEXT}

レビュー観点:
1. このフェーズ別割り振りで本当にコスト下がるか?(計算検証)
2. miniに任せて事故るリスクが高いフェーズはどれか?
3. o3-miniとgpt-4oだとどちらが「設計レビュー」に向くか?(2026年6月時点)
4. 「1工程8往復」の往復数設計は妥当か?(過剰/不足)
5. ジョブズが見落としてるリスクを3つ挙げよ
6. 改善案を具体的に(モデル名+理由)

出力形式:
## 総評(3行以内)
## コスト試算の妥当性
## 各フェーズの再評価
## ジョブズが見落としてるリスク
## 最終推奨構成(モデル名明記)
"""

print("=" * 60)
print("GPT-4o 壁打ちラウンド1: フェーズ別モデル割り振り案")
print("=" * 60)

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": PROMPT}],
    temperature=0.3,
)

result = response.choices[0].message.content
print(result)
print()
print("=" * 60)
print(f"使用トークン: in={response.usage.prompt_tokens} / out={response.usage.completion_tokens}")
cost = response.usage.prompt_tokens * 2.5 / 1_000_000 + response.usage.completion_tokens * 10 / 1_000_000
print(f"今回コスト: ${cost:.4f}")
print("=" * 60)
