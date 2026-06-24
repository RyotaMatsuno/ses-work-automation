# -*- coding: utf-8 -*-
"""mail_pipeline dedup破損 + マッチング精度問題の壁打ち(GPT-5.4)"""

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

prompt = """SES業務自動化システムで以下の事案が発生。GPT視点で最善の対応を提案してほしい。

【事案】
mail_pipeline(IMAP→Notion案件DB登録、30分Cron)のdedup破損で、5月12日受信メールが6月14日に重複2件で新規登録された。

事実:
- 元メール: SBT営業 sales@sbt-inc.co.jp / 件名「【SBT◆案件】独占 ★ 業務サポート案件 ★」/ 受信2026-05-12 18:43 JST
- Notion案件DB(343450ff-...)に2件重複登録: created_time=2026-06-14 16:04 UTC, 17:03 UTC
- ステータス「募集中」のままLINE通知で「3日前」と表示
- 過去5月27日に正しく登録され、6月5日に「終了」マークされた同じ案件レコード2件が別途存在
- 判断マニュアル: 案件情報は4営業日前まで有効。5月12日→6月17日=36日経過、完全に鮮度切れ
- matching_v3が走って、人員1名にマッチング結果として通知された(これは別問題、Q5参照)

過去インシデント:
2026-06初頭にFETCH_LIMIT=2000 + spam filter欠落 + processed_ids dedup破損で$50/日のコスト暴走

【質問1】重複登録2件の処理方法
- Notion案件DBで「終了」ステータスに変更 vs 削除 vs アーカイブ vs 過去終了済みレコードとマージ
- 既に matching_v3 が1名にマッチング通知済み(=その人員の所属に岡本が既に意向確認メール送信した可能性)も考慮
- ベストプラクティスは?

【質問2】6月14日の他の汚染メール調査方法
案件DBから「created_time=2026-06-14」のレコードを全件抽出 → 案件詳細フィールド(rich_text、メール本文を保存)から元メールDateを抽出 → 差分が4営業日以上なら汚染候補。
具体的なクエリ設計、誤検出フィルタ、Notion API + Python実装の勘所を提示してほしい。

【質問3】mail_pipeline の created_time 戦略
現状: Notion登録時にDateヘッダではなく現在時刻がcreated_timeになる
対策候補:
A. Notion専用プロパティ「受信日」(date型)を新設し、メールDateを保存
B. 案件名先頭にメール日付を含める
C. LINE通知時はcreated_timeでなく「受信日」プロパティを表示
pros/cons評価と推奨案、既存レコードへのマイグレーション計画を。

【質問4】mail_pipeline dedup破損の原因仮説と調査優先順位
過去はFETCH_LIMIT=2000 + spam filter欠落 + dedup破損だった。今回は何が原因か。
原因仮説top3と、効率的な切り分け手順を。

【質問5】matching_v3で1件しか返らない問題(後日見直し用、簡潔に)
SBT案件で matching_v3 が人員1名のみ返した。SES母集団15名弱。
CEO証言: 「スキル厳密チェックせず単価が合えばマッチング」ルールに過去1人だけ変更した記憶あり。
matching_v3:
- 平日8:00 AM 自動実行(ルールベース、LLM未使用)
- 3層判定 NG/REVIEW/MATCH
- 必須スキル全○ + 並行スコア5未満 → MATCH
精度低下の原因仮説top3と、後日見直しの着眼点を簡潔に。

JSON形式で:
{
  "q1_duplicate_handling": {"recommended": "", "reasoning": "", "pre_check_before_action": ""},
  "q2_pollution_scan": {"query_design": "", "thresholds": "", "false_positive_filter": "", "implementation_notes": ""},
  "q3_created_time_strategy": {"recommended_letter": "A/B/C/combo", "design": "", "migration_plan": ""},
  "q4_dedup_root_cause": {"top3_hypotheses": [{"hypothesis": "", "evidence_to_check": ""}], "investigation_order": []},
  "q5_matching_accuracy_for_later": {"top3_hypotheses": [], "review_points": [], "ses_caveat": ""}
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
    out_path = BASE / "auto_coder" / "wall_hitting_mail_pipeline_bug.md"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(
        f"# mail_pipeline dedup破損 壁打ち\n\n日時: {datetime.now().isoformat()}\nmodel: gpt-5.4\nusage: {json.dumps(usage, ensure_ascii=False)}\n\n---\n\n{text}\n",
        encoding="utf-8",
    )
    print(f"\n[saved] {out_path}")
else:
    print(f"エラー: {res.status_code} {res.text[:500]}")
