"""
Step A Phase②.5: DAILY_CALL_LIMIT 経営判断レビュー
o3にコスト暴走再発リスクと運用効率のバランスを評価させる
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

CONTEXT = """
# 事業背景
SES営業自動化システム(2名体制、松野CEO+岡本パートナー)
売上規模: 月15名稼働、粗利フロア5万/人=月75万以上

# 既存安全装置
- CostGuard: $8/日・$140/月で自動停止(既に稼働中・全LLM呼出が通る)
- ledger.py: 全スクリプト横断のコスト集計
- LLM_KILL=1: 即時停止フラグ
- gate_checker DAILY_CALL_LIMIT: 1日10回(改修対象)

# 過去事故
2026-06-02 mail_pipeline FETCH_LIMIT上限なし → $50.88/日暴走発生
教訓: 「上限なし」「上限大きすぎ」は事故の元

# 改修後の想定
- フェーズ別モデル切替で月$58想定(1日5タスク×6工程×8往復=240回/日)
- DAILY_CALL_LIMIT=10 のままだと機能停止
- どこまで上限を上げるか経営判断必要

# 4つの選択肢
A. 据置(10) → 機能停止、却下確定
B. 段階解放: 50 → 100 → 240 と週次で段階引上げ、各段階で観測
C. 一気に300上限、CostGuard$8/日が金額ストッパー
D. DAILY_CALL_LIMIT廃止、CostGuard($8/日)一元化、二重の壁を統一
"""

PROMPT = f"""
あなたは経営リスク判断の専門家。SES営業自動化システムの上限設計について、
過去の暴走事故を踏まえつつ、運用効率と安全性のバランスを判断せよ。

{CONTEXT}

【評価観点】
1. CostGuard($8/日)があるのにDAILY_CALL_LIMITも併存させる二重防御の意味
2. 過去事故($50.88/日)はDAILY_CALL_LIMIT廃止で再発するか?
3. 段階解放(B)は「観測する手間」がジョブズ運用を圧迫しないか?
4. 単一防御(D)の心理的安心感の欠如は問題か
5. 1日10回→240回の24倍ジャンプは何を意味するか
6. もし暴走したら誰がどう気づくか(検知ラグ)

【追加考慮】
- 松野は「物忘れ・口出し可視化」を求めている → 大量壁打ち必須
- 松野はコスト暴走経験から保守的傾向
- ジョブズ(Claude)は確認なしで実装に流れがち

【出力形式】
## 結論(1択、理由3行以内)
## 各案の致命的弱点
## 推奨案の運用ルール(具体的に)
## 暴走検知の追加実装提案(あれば)
## 経営判断として一番大切なポイント
"""

print("=" * 60)
print("Step A Phase②.5: DAILY_CALL_LIMIT経営判断レビュー (o3)")
print("=" * 60)

response = client.chat.completions.create(
    model="o3",
    messages=[{"role": "user", "content": PROMPT}],
    reasoning_effort="high",
)

result = response.choices[0].message.content
print(result)
print()
print(f"トークン: in={response.usage.prompt_tokens} / out={response.usage.completion_tokens}")
cost = response.usage.prompt_tokens * 2 / 1_000_000 + response.usage.completion_tokens * 8 / 1_000_000
print(f"コスト: ${cost:.4f}")
