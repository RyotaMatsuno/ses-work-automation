# -*- coding: utf-8 -*-
"""auto_coderコスト問題の壁打ち(GPT-5.4)"""

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

prompt = """あなたはAI/LLM自動化システムの専門家です。2026年6月時点の最新情報で回答してください。

【現状】
SES業務自動化システムで、「pending_tasks/に指示書を置くだけで自動コード実装が走る」装置(auto_coder)を構築したい。

既存インフラ:
- jobz-command(localhost HTTP server, port 8765)
- task_auto_runner(5分Cronスキャン pending_tasks/ → 自動実装 → done/移動、3回リトライ、blocked退避)
- ThreadPoolExecutor×5並列処理
- CostGuard v2(ledger.py $8/日, cost_guard.py $20/日のハードリミット)
- Notion / LINE / Gmail / Google Calendar / Google Drive(全MCP接続済み)
- Cursor Pro $20/月(現状利用、Sonnet 4.6使い放題、26%消費)
- Anthropic Claude Max プラン加入済み(月$100または$200)

技術的障害:
Anthropic Claude Code CLI 2.1.144が対話モード前提化し、--dangerously-skip-permissionsがEdit/Write操作を抑止しなくなった。pending_tasksを完全自動実装させる構成ができない状態。

検討案:
案A: auto_coder自作(Anthropic SDK直叩き+自前tool loop) → 月$50程度のAPI課金見込み
案B: Cursor手動投入継続 → 追加課金なし、CEO自身がCursor開く手間(1日5分程度)
案C: OpenAI Codex CLI再導入 → 内部OpenAI API課金が発生(額不明)

CEO要望:
追加課金をほぼ増やさず、Cursor手動投入を完全自動化したい。月コスト上限$10以下が理想、$30まで許容。

【質問1】Claude Code CLI 2.1.144の対話モード問題を回避し、Edit/Write自動承認させる方法はあるか?
- subprocess.Popen + stdin自動応答パターン
- expect/pty/winpty で対話シミュレート
- 環境変数(CLAUDE_AUTO_APPROVE / CLAUDE_NON_INTERACTIVE等)
- バージョンダウングレード(2.1.143以前なら動くか)
- Hidden flag / debug mode / 別の自動化フラグ
具体的なコマンド・コード例があれば提示。

【質問2】Anthropic Max プラン($100〜$200/月)の活用余地は?
- 2026年6月時点でMaxプランにAPIクレジット枠は含まれるか?
- Claude Code CLIをMax credentialsで自動化する手段は?
- Max加入者向けAPI割引・特典の存在
2026年6月時点の最新仕様で回答。

【質問3】月$10以下、最大$30で「pending_tasks自動コーディング装置」を実現する代替案を3案以上提示。
- DeepSeek V3/R1で構築(料金、コード品質、Sonnet比)
- GPT-4o-mini / o3-miniで構築
- Gemini 2.5 Flash / Flash-Lite で構築
- Aider(OSS) + 安いAPI
- Cline / Continue / OpenHands(OSS)の自動化フック化
- ローカルLLM(Ollama + Qwen 2.5 Coder 32B等)のWindows現実性
各案: 月コスト試算 / コード品質 / 実装難度 / task_auto_runner統合性を評価。

JSON形式で回答:
{
  "q1_claude_code_workaround": {
    "feasibility": "low/medium/high",
    "methods": [{"name": "", "steps": "", "risk": ""}],
    "recommended": ""
  },
  "q2_max_plan": {
    "api_credit_included": "yes/no/unknown_as_of_202606",
    "automation_path": "",
    "discount_for_max_users": "",
    "notes": ""
  },
  "q3_alternatives": [
    {"approach": "", "monthly_cost_usd": 0, "code_quality_vs_sonnet": "lower/comparable/higher", "implementation_effort_days": 0, "task_runner_compat": "yes/no/partial", "notes": ""}
  ],
  "ceo_recommendation": {
    "if_target_under_10usd": "",
    "if_allow_up_to_30usd": "",
    "reasoning": ""
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
    # 結果を保存
    out_path = BASE / "auto_coder" / "wall_hitting_cost_alternatives.md"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(
        f"# auto_coderコスト問題の壁打ち\n\n日時: {datetime.now().isoformat()}\nmodel: gpt-5.4\nusage: {json.dumps(usage, ensure_ascii=False)}\n\n---\n\n{text}\n",
        encoding="utf-8",
    )
    print(f"\n[saved] {out_path}")
else:
    print(f"エラー: {res.status_code} {res.text[:500]}")
