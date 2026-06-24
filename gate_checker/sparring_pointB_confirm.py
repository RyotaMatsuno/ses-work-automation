#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""論点B確定+次ステップ進行可否のGPT-5.4 壁打ち批判"""

import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, "C:/Users/ma_py/OneDrive/デスクトップ/ses_work")

from dotenv import load_dotenv

load_dotenv("C:/Users/ma_py/OneDrive/デスクトップ/ses_work/config/.env")

from openai import OpenAI

from common.ledger import can_spend, record

MODEL = "gpt-5.4"

PROMPT = """あなたは経営参謀AIの上位レビュアーです。以下の判断を批判的に検証してください。
甘い同意は不要、見落とし・前提誤り・経済合理性の穴を最優先で指摘してください。

# 背景
SES(System Engineer Staffing)事業のCEO松野は2人体制で年商を伸ばしている。
コード実装はCursor IDE経由でClaude Sonnet 4.6に投げている。
本日、ジョブズ(経営参謀AI)が「Cursor統合戦略(論点B)」を再評価し、案Aで確定した。

# 前チャットの3案(再掲)
- 案A: 現状維持(Sonnet 4.6 Cursor経由)
- 案B: Sonnet 4.6 + gpt-5.3-codex 併用(codexはOpenAI API直接)
- 案C: 全部GPT-5系(Cursor解約してOpenAI API)

# 本日判明したCursor設定UI実測値(スクショ確認済み)
- Current Plan: Cursor Pro $20/月 (リセット日 7/9)
- Included in Pro 含有枠 Total: 6% (サイクル7日経過時点)
- 内訳: 8% Auto / 0% API used
  - Auto = Cursor提供モデル(Composer 2.5 / Sonnet 4.6 / その他)
  - API = ユーザー登録の自分のAPIキー経由
- On-Demand Spending: Disabled (超過時の自動API課金OFF)
- 表示中のアップグレード提案: Pro+ $60/mo (3倍枠)
- API Keys: Anthropic Key ON状態 (登録済み)、OpenAI Key OFF
- Cursor公式pricing FAQ: "Every plan includes a set amount of model usage. On-demand usage allows you to continue using models after your included amount is consumed, billed in arrears."

# 線形換算
6% / 7日 × 30日 = 約26% (月末まで Pro $20 含有枠の約26%消費見込み、74%余裕)

# ジョブズの確定判断
**案A(Cursor Pro $20/月 継続)で確定。月コスト固定$20、API課金ゼロ。**

理由:
1. 含有枠26%消費見込みで Pro$20 内に十分収まる
2. API used = 0% なので Anthropic Key ON は機能していない(保険状態)
3. On-Demand Disabled で超過時の課金も遮断済み
4. 案B(codex併用)は codex従量分が乗るため増額。現状で枠余ってるので不要
5. 案C(Pro解約+全GPT API)は Pro$20 含有枠を捨てる損
6. Pro+ $60(3倍枠)アップグレードも不要(現Pro26%消費なので)

付随アクション:
- 推奨(任意): Anthropic Key を OFF にする (現状0%なので影響ゼロ、Pro超過時のAPI課金リスクを排除)

# 前チャットで確定済み(本日変更なし)
- 論点A(gate_checker フェーズ別モデル割振): gpt-5.4-mini/5.4/5.3-codex 月$3.94
- 論点C(DAILY_CALL_LIMIT 30→60→90段階値, 二次壁打ち設計)
- 論点D(安全装置4つロードマップ Week1: 装置2+3)

これらは全てOpenAI API直接呼出系で、Cursor IDEとは独立系統。
よって本日の論点B変更は論点A/C/Dに影響しないと判断している。

# 次のアクション
3点セット(CLAUDE.md/SPEC.md/TASKS.md)作成 → pending_tasks/に作業指示書保存
→ Cursor(Sonnet 4.6)に実装を投げる

# 批判してほしい点(全て答えてください)
Q1. 案A確定の判断は経済合理的か?見落としているコスト構造はないか?
Q2. 「API used = 0%」の解釈は正しいか?(他の解釈余地はないか?例:Auto内にAPI課金が含まれている等)
Q3. 線形換算(6%/7日→26%/月)の前提は妥当か?月後半に作業集中する季節性などはどう扱うべきか?
Q4. Anthropic Key OFFのデメリットはあるか?(例:Cursor障害時のフォールバック、特定モデル使用時の挙動など)
Q5. 論点B確定後に論点A/C/Dへの影響が「なし」とした判断は本当に正しいか?何か繋がりはないか?
Q6. 次ステップ(3点セット作成+作業指示書 pending_tasks/ 保存)に進んでよいか?何か先にやるべきことはないか?
Q7. 重大欠陥(STOP級)があれば最初に明示してください。なければ「STOP級なし」と書いてから各Qに回答。

簡潔に、ただし根拠は具体的に。"""

# CostGuard
ok = can_spend(est_in=2000, est_out=2000, model=MODEL)
if not ok:
    print("[CostGuard] 拒否されました")
    sys.exit(1)

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

print(f"[INFO] {MODEL} 壁打ち開始...")

# Responses API (gpt-5.x系)
try:
    resp = client.responses.create(
        model=MODEL,
        input=PROMPT,
        reasoning={"effort": "medium"},
    )
    text = resp.output_text
    in_tok = resp.usage.input_tokens
    out_tok = resp.usage.output_tokens
except Exception as e:
    print(f"[ERROR] Responses API失敗: {e}")
    # Fallback: chat completions
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT}],
    )
    text = resp.choices[0].message.content
    in_tok = resp.usage.prompt_tokens
    out_tok = resp.usage.completion_tokens

record(in_tokens=in_tok, out_tokens=out_tok, model=MODEL, script="sparring_pointB_confirm.py")

# 結果保存
os.makedirs("gate_checker/results", exist_ok=True)
with open("gate_checker/results/sparring_pointB_confirm_result.txt", "w", encoding="utf-8") as f:
    f.write(text)

print("=" * 80)
print(text)
print("=" * 80)
print(f"\n[USAGE] in={in_tok}, out={out_tok}")
