# -*- coding: utf-8 -*-
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 今日の実行コストを確認
log = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\pipeline.log")
lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
today = "2026-06-15"
today_lines = [l for l in lines if l.startswith(f"[{today}")]

# 1回の実行あたりの処理件数とコストを推定
runs = []
current = {"start": None, "fetched": 0, "registered": 0}
for l in today_lines:
    if "取得完了: 合計" in l:
        import re

        m = re.search(r"合計(\d+)件", l)
        if m:
            current["fetched"] = int(m.group(1))
    if "メールパイプライン v5.2 完了" in l:
        runs.append(dict(current))
        current = {"start": None, "fetched": 0, "registered": 0}

print("=== 1実行あたりの処理件数 ===")
for i, r in enumerate(runs):
    print(f"  実行{i + 1}: 取得{r['fetched']}件")

# 実際のAPIコスト
cost_log = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\usage_tracker\cost_log.jsonl")
if cost_log.exists():
    mail_costs = []
    with cost_log.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                e = json.loads(line)
                if e.get("ts", "").startswith(today) and "mail_pipeline" in e.get("script", ""):
                    mail_costs.append(e.get("cost_usd", 0))
            except:
                pass
    total_mail = sum(mail_costs)
    calls = len(mail_costs)
    print("\n=== mail_pipeline 本日コスト ===")
    print(f"  総コスト: ${total_mail:.4f}")
    print(f"  APIコール数: {calls}回")
    if calls > 0:
        print(f"  1コールあたり: ${total_mail / calls:.4f}")

    # 600件/回に増やした場合の試算
    current_per_run = total_mail / max(len(runs), 1)
    scale = 600 / 200  # 3倍
    print("\n=== 600件/回に増やした場合の試算 ===")
    print(f"  現在: ${current_per_run:.4f}/回 × {len(runs)}回 = ${total_mail:.4f}/日")
    print(f"  600件なら: ${current_per_run * scale:.4f}/回 × {len(runs)}回 = ${total_mail * scale:.4f}/日")
    print(f"  → 日次上限$8との比較: {'OK' if total_mail * scale < 8 else 'NG（超過）'}")
