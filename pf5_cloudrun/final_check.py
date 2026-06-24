import sys
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Webhookにテストリクエストを送ってLLM_KILLフラグ未設定（通常状態）で200が返るか確認
url = "https://line-webhook-74735301292.asia-northeast1.run.app"
try:
    r = requests.get(url, timeout=10)
    print(f"GET / -> status={r.status_code}")
except Exception as e:
    print(f"接続エラー: {e}")

# ledgerのコスト確認（Phase3以降に実行があれば記録されているはず）
base = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
sys.path.insert(0, str(base))
try:
    # importキャッシュをクリア
    import importlib

    import common.ledger as ledger_mod

    importlib.reload(ledger_mod)
    from common.ledger import daily_total, monthly_total

    print(f"\nledger: today=${daily_total():.4f}  month=${monthly_total():.4f}")
except Exception as e:
    print(f"ledger error: {e}")

# cost_state.json の確認
cost_state = base / "common" / "cost_state.json"
if cost_state.exists():
    import json

    data = json.loads(cost_state.read_text(encoding="utf-8"))
    print(f"cost_state.json: {json.dumps(data, ensure_ascii=False, indent=2)}")
else:
    print("cost_state.json: まだ存在しない（次回タスク実行待ち）")

# スケジューラの次回実行時刻を再確認
import subprocess

print("\n=== スケジューラ次回実行時刻 ===")
for t in ["SES_MailPipeline", "SES_MatchingV3", "SES_CostGuard"]:
    r2 = subprocess.run(
        ["schtasks", "/query", "/tn", t, "/fo", "LIST"],
        capture_output=True,
        text=True,
        encoding="cp932",
        errors="replace",
    )
    if r2.returncode == 0:
        lines = [l for l in r2.stdout.splitlines() if any(k in l for k in ["次回", "状態"])]
        print(f"  [{t}]")
        for l in lines:
            print(f"    {l.strip()}")
