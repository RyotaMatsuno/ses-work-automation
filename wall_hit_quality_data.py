# -*- coding: utf-8 -*-
"""Gemini Flash品質の具体データ壁打ち(GPT-5.4)"""

import json
import sys
from datetime import datetime
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import dotenv_values

BASE = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
env = dotenv_values(BASE / "config" / ".env")
API_KEY = env.get("OPENAI_API_KEY", "")

prompt = """あなたはAIコーディングエージェントのベンチマーク・実測データに詳しい専門家です。
2026年6月時点の最新ベンチマークスコア・実測データに基づいて回答してください。
推測でなく、可能な限り具体的な数値で答えてください。データが不確実な場合はその旨を明記してください。

【背景】
SES業務自動化のため「pending_tasks/に指示書を置くだけで自動コード実装」する装置(agentic coder, 自前tool loop)を構築したい。
候補LLM: Gemini 2.5 Flash, DeepSeek V3, GPT-4o-mini, Claude Sonnet 4.6
タスク粒度: Python script修正(50〜300行)、API置換、バグ修正、CostGuard統合追加、Notion REST呼び出し追加など、中規模実装が中心。
既存環境: Windows, OneDrive配下, 日本語パス, Notion direct REST必須, ledger.py/cost_guard.py 2層コスト管理 など、暗黙の環境制約多数。

【質問1: 公式ベンチマーク数値】
2026-06時点の最新数値で以下を埋めてください。
- SWE-bench Verified スコア(%): Sonnet 4.6 / Gemini 2.5 Flash / Gemini 2.5 Pro / DeepSeek V3 / GPT-4o-mini / o3-mini
- Aider Polyglot Leaderboard 順位/スコア: 同上
- LiveCodeBench スコア: 同上
- HumanEval+: 同上
データ不確実な場合は「推定」と明記してください。

【質問2: agentic coding 実測経験】
Gemini 2.5 Flash を agentic coding(tool use loop, file edit, command exec)で使った場合の実測:
- 中規模Pythonタスク(50〜300行修正)での一発成功率
- 失敗時のリカバリ成功率(再試行で成功する確率)
- ファイル編集(edit_file old_str/new_str置換)の精度
- テストコード生成の品質
Sonnet 4.6, GPT-4o-mini, DeepSeek V3 との数値比較。

【質問3: 暗黙の環境制約への対応力】
SES業務環境では「ハマりパターン」が多数あります:
- Windows OneDrive配下でのファイルロック(WinError 5)
- 日本語パス文字化け
- pythonw vs python の stdout 違い
- Notion API でMCP不可→ direct REST 必須
- ledger.py / cost_guard.py の2層チェック忘れ
これらを CLAUDE.md に明示的に書けば、各モデルは回避できるか?
Sonnet 4.6 vs Gemini 2.5 Flash で「指示への忠実度」の差は?

【質問4: SES業務での想定手戻り率】
上記タスク粒度・環境前提で、auto_coder を Gemini 2.5 Flash で運用した場合:
- 月50タスク処理する想定の一発成功率予測
- blocked率(3回リトライしても失敗)
- 手戻り発生時のCEO手動所要時間予測(1タスクあたり何分)
Sonnet 4.6 で同じ運用した場合との比較。

【質問5: 結論】
- Gemini 2.5 Flash は SES業務 agentic coder のメインLLMとして実用に耐えるか?
- 「品質悪くて手戻りが多い」リスクの定量評価
- 2026-06時点で最もコストパフォーマンスが良いモデルは?

JSON形式で:
{
  "q1_benchmarks": {
    "swe_bench_verified": {"sonnet_4_6": null, "gemini_2_5_flash": null, "gemini_2_5_pro": null, "deepseek_v3": null, "gpt_4o_mini": null, "o3_mini": null, "data_confidence": "high/medium/low"},
    "aider_polyglot": {"sonnet_4_6": null, "gemini_2_5_flash": null, "deepseek_v3": null, "gpt_4o_mini": null, "data_confidence": "high/medium/low"},
    "livecodebench": {"sonnet_4_6": null, "gemini_2_5_flash": null, "deepseek_v3": null, "data_confidence": "high/medium/low"}
  },
  "q2_agentic_coding": {
    "gemini_flash_one_shot_success_rate_pct": null,
    "gemini_flash_retry_success_rate_pct": null,
    "edit_file_precision": "",
    "test_generation_quality": "",
    "vs_sonnet_4_6": "",
    "data_confidence": "high/medium/low"
  },
  "q3_instruction_following": {
    "sonnet_4_6_score_out_of_10": null,
    "gemini_2_5_flash_score_out_of_10": null,
    "deepseek_v3_score_out_of_10": null,
    "gpt_4o_mini_score_out_of_10": null,
    "notes": ""
  },
  "q4_ses_projection": {
    "gemini_flash_monthly_50_tasks": {
      "one_shot_success_rate_pct": null,
      "blocked_rate_pct": null,
      "ceo_manual_minutes_per_blocked": null,
      "total_ceo_minutes_per_month": null
    },
    "sonnet_4_6_monthly_50_tasks": {
      "one_shot_success_rate_pct": null,
      "blocked_rate_pct": null,
      "ceo_manual_minutes_per_blocked": null,
      "total_ceo_minutes_per_month": null
    }
  },
  "q5_conclusion": {
    "gemini_flash_practical": "yes/conditional/no",
    "rework_risk_level": "low/medium/high",
    "rework_risk_quantified": "",
    "best_cost_performance_2026_06": "",
    "final_recommendation": ""
  }
}
"""

res = requests.post(
    "https://api.openai.com/v1/chat/completions",
    headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    json={"model": "gpt-5.4", "max_completion_tokens": 6000, "messages": [{"role": "user", "content": prompt}]},
    timeout=180,
)
if res.status_code == 200:
    j = res.json()
    text = j["choices"][0]["message"]["content"]
    usage = j.get("usage", {})
    print(text)
    print("\n---\nusage:", json.dumps(usage, ensure_ascii=False))
    out_path = BASE / "auto_coder" / "wall_hitting_quality_data.md"
    out_path.write_text(
        f"# Gemini Flash品質具体データ壁打ち\n\n日時: {datetime.now().isoformat()}\nmodel: gpt-5.4\nusage: {json.dumps(usage, ensure_ascii=False)}\n\n---\n\n{text}\n",
        encoding="utf-8",
    )
    print(f"\n[saved] {out_path}")
else:
    print(f"エラー: {res.status_code} {res.text[:500]}")
