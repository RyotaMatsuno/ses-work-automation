# -*- coding: utf-8 -*-
"""mail_pipeline復旧戦略 + 5%段階拡大検証 壁打ち(GPT-5.4)"""

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

prompt = """SES業務自動化システムで深刻な事案。復旧戦略の最適解を判断したい。

【事案サマリ】
- mail_pipeline(IMAP→Notion案件DB/EngineerDB登録、30分Cron)が6/15 19:43 JST以降ほぼ停止
- 6/16 11:54 にコード修正(119行追加、67567バイト)→ それが引き金で Notion 500 連発
- 6/16丸日: 稼働ログ0行 / 6/17は3回起動するが各1行のNotion 500エラーで即終了
- 案件登録ペース 6/11(26件)→6/12(10件)→6/13(0)→6/14(0)→6/15(143一斉)→6/16(0)→6/17(0)
- 約5日分20,000件のメールが未処理で溜まっている
- Notion API 自体は正常(直接queryテスト 200 OK確認済)

【既存の安全装置(SPEC確認済)】
SPEC_costfix.md(2026-06-04):
- FETCH_LIMIT=200, PROCESS_LIMIT=50, SINCEフィルタ7日以内
- processed_ids上限10000件
- 日次$2でAPIスキップ(call_claude先頭でget_today_cost_usd()チェック)
- Haiku 4.5 + Batch API

SPEC_phase1.md(Global Kill-Switch):
- HOURLY_LIMIT_USD=3.0(警告)
- DAILY_SOFT_LIMIT_USD=6.0(警告のみ)
- DAILY_LIMIT_USD=8.0(全タスク+Cloud Run即停止)
- 7タスク(SES_MailPipeline/MatchingV3/jobz_importer等)を即時無効化

【過去インシデント】
2026-06頃: FETCH_LIMIT=2000+dedup破損 → $9.30/日 → Auto-recharge発動 → 一時$50/日暴走

【CEO証言】
「5%ずつ段階拡大」運用に過去決めた記憶がある(SPEC等に明示なし)
コスト面の慎重対応強く要望

【復旧シナリオ】
A. mail_pipeline.py を .bak_phase4(6/4版、当時稼働実績あり)に即巻き戻し → フル稼働 → 既存安全装置に頼る
B. 巻き戻し + 一時的にPROCESS_LIMIT=10/回(480件/日)で1〜2日様子見 → 異常なければ50/回に戻す
C. 巻き戻し + 段階拡大ロジック新規実装(1日目5%=120件、2日目10%=240件...)
D. 巻き戻しせず Cursor 根本修正待ち(数日案件登録停止)

【質問1】既存安全装置でA案フル稼働は安全か
6/4版+全安全装置(日次$2/$8/Cloud Run kill)で復旧時に$50/日インシデント再発リスクの定量評価。

【質問2】5日分20,000件溜まり処理戦略
SINCEフィルタ7日内なのでfetch対象。PROCESS_LIMIT=50/回 × 30分Cron = 2,400件/日 → 完全消化に約8.3日。これは妥当か、もっと早く安全に処理する方法は?

【質問3】CEOの「5%ずつ段階拡大」をどう解釈すべきか
既存のPROCESS_LIMIT=50 + 日次$2上限が事実上の段階拡大装置として機能していると考えていいか。
追加で段階拡大ロジックを実装する場合の具体的設計と、不要な可能性も含めて評価。

【質問4】A/B/C/D 推奨シナリオ
コスト・リスク・復旧スピード・実装労力のバランスで最適解は?

【質問5】コスト試算
Haiku 4.5 + Batch API想定:
- 復旧初日(2,400件処理、うち分類+抽出+matching v2)のコスト見込み
- 5日分20,000件完全消化までのトータル
- 通常運用時の月額予測

JSON形式で:
{
  "q1_a_safety": {
    "risk_level_50usd_recurrence": "low/medium/high",
    "estimated_max_daily_cost_usd": null,
    "reasoning": "",
    "guard_effectiveness": ""
  },
  "q2_5day_strategy": {
    "default_8d_consumption_acceptable": "yes/no",
    "faster_alternatives": [],
    "recommended_approach": ""
  },
  "q3_5percent_interpretation": {
    "existing_guards_sufficient": "yes/no/partial",
    "ceo_memory_likely_referring_to": "",
    "if_implement_5percent_design": "",
    "recommendation": ""
  },
  "q4_recommended_scenario": {
    "best": "A/B/C/D",
    "second_best": "A/B/C/D",
    "reasoning": "",
    "specific_steps": []
  },
  "q5_cost_estimate": {
    "day1_2400_emails_usd": null,
    "total_recovery_20000_emails_usd": null,
    "monthly_normal_operation_usd": null,
    "worst_case_daily_usd": null
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
    out = BASE / "auto_coder" / "wall_hitting_recovery_strategy.md"
    out.write_text(
        f"# mail_pipeline復旧戦略 壁打ち\n\n日時: {datetime.now().isoformat()}\nmodel: gpt-5.4\nusage: {json.dumps(usage, ensure_ascii=False)}\n\n---\n\n{text}\n",
        encoding="utf-8",
    )
    print(f"\n[saved] {out}")
else:
    print(f"エラー: {res.status_code} {res.text[:500]}")
