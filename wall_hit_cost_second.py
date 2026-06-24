# -*- coding: utf-8 -*-
"""復旧戦略 コスト面セカンドオピニオン(GPT-5.4)"""

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

prompt = """前回相談したmail_pipeline復旧戦略について、コスト面に絞ったセカンドオピニオンが欲しい。
楽観的すぎないか、見落としがないかを厳しめに検証してください。

【前回回答(あなたの試算)】
- 復旧初日(2,400件): $2
- 20,000件完全消化トータル: $16.7
- 通常運用月額: $60
- 最悪日次(Kill-Switch発動時): $8

【背景(再掲)】
- mail_pipeline: Haiku 4.5 + Batch API + ルール分類
- 既存ガード: call_claude先頭で日次$2チェック / Global Kill-Switch日次$8 / FETCH_LIMIT=200 / PROCESS_LIMIT=50
- 過去インシデント: FETCH_LIMIT=2000+dedup破損で$9.30/日 → Auto-recharge $40発動 → 一時$50/日
- CEOは別件(auto_coder月$50追加)で慎重判断。月$60は法人化準備中の事業者として許容範囲か微妙

【追加検証要件】
1. 上記試算は楽観的すぎないか(現実的 vs 楽観的 vs 悲観的)
2. 既存$2/$8ガードのカバレッジ漏れ(mail_pipeline以外の連鎖呼び出しでガード回避されないか)
3. Anthropic Auto-recharge $40 再発リスクと推奨対策
4. matching_v2 JSONDecodeError 再試行による隠れコスト
5. mail_attachment_importer や matching_v3 など連動システムのコスト影響
6. 段階拡大運用中の追加コスト(疎通テスト、メトリクス記録、手動確認等)
7. 「月$60」がCEO慎重姿勢に対して許容範囲か
8. 万一$8/日が連続発動した場合の月最大コスト(=ガード上限張り付き想定)
9. 復旧期間中(8.3日)に matching_v2 が backlog消化と共に過剰起動するリスク

JSON形式で厳しめに:
{
  "q1_estimate_validity": {
    "day1_2usd": "realistic/optimistic/pessimistic",
    "total_recovery_167usd": "realistic/optimistic/pessimistic",
    "monthly_60usd": "realistic/optimistic/pessimistic",
    "realistic_revised_estimate": {
      "day1_usd": null,
      "total_recovery_usd": null,
      "monthly_usd": null
    },
    "overlooked_costs": []
  },
  "q2_guard_coverage_gaps": {
    "gaps_found": [],
    "severity": "low/medium/high"
  },
  "q3_auto_recharge_risk": {
    "level": "low/medium/high",
    "recommended_actions": [],
    "should_disable_before_recovery": "yes/no/conditional"
  },
  "q4_matching_v2_retry_cost": {
    "estimated_extra_usd_per_day": null,
    "mitigation": ""
  },
  "q5_linked_system_cost": {
    "mail_attachment_importer_impact_usd": null,
    "matching_v3_impact_usd": null,
    "total_linked_extra_usd": null
  },
  "q6_phased_test_overhead": {
    "extra_usd_during_8d_recovery": null,
    "notes": ""
  },
  "q7_ceo_60usd_acceptability": {
    "verdict": "acceptable/marginal/unacceptable",
    "reasoning": "",
    "cost_reduction_options": []
  },
  "q8_worst_case_month": {
    "8usd_daily_continuous_monthly_usd": null,
    "probability": "low/medium/high"
  },
  "q9_matching_v2_overrun_risk": {
    "level": "low/medium/high",
    "mitigation": ""
  },
  "final_recommendation": {
    "go_nogo": "GO/CONDITIONAL_GO/NOGO",
    "conditions_if_any": [],
    "key_red_flags_to_watch": []
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
    out = BASE / "auto_coder" / "wall_hitting_cost_second_opinion.md"
    out.write_text(
        f"# 復旧コスト面セカンドオピニオン\n\n日時: {datetime.now().isoformat()}\nmodel: gpt-5.4\nusage: {json.dumps(usage, ensure_ascii=False)}\n\n---\n\n{text}\n",
        encoding="utf-8",
    )
    print(f"\n[saved] {out}")
else:
    print(f"エラー: {res.status_code} {res.text[:500]}")
