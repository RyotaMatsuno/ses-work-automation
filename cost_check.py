import json
import sys
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
sys.path.insert(0, str(base))

# ledger経由
print("=== ledger コスト確認 ===")
try:
    import importlib

    import common.ledger as lm

    importlib.reload(lm)
    from common.ledger import daily_total, monthly_total

    d = daily_total()
    m = monthly_total()
    print(f"  today  : ${d:.4f}")
    print(f"  month  : ${m:.4f}")
except Exception as e:
    print(f"  ledger error: {e}")

# cost_state.json
print("\n=== cost_state.json ===")
cs = base / "common" / "cost_state.json"
if cs.exists():
    data = json.loads(cs.read_text(encoding="utf-8"))
    print(json.dumps(data, ensure_ascii=False, indent=2))
else:
    print("  未生成")

# cost_log（直近30件）
print("\n=== cost_log 直近30件 ===")
for log_name in ["cost_log.jsonl", "common/cost_log.jsonl", "logs/cost_log.jsonl"]:
    lp = base / log_name
    if lp.exists():
        lines = lp.read_text(encoding="utf-8", errors="replace").splitlines()
        print(f"  ファイル: {log_name}  ({len(lines)}件 / {lp.stat().st_size // 1024}KB)")
        today_str = str(date.today())
        today_lines = [l for l in lines if today_str in l]
        print(f"  本日分: {len(today_lines)}件")
        for l in today_lines[-10:]:
            try:
                d2 = json.loads(l)
                ts = d2.get("timestamp", "")[:16]
                cost = d2.get("cost_usd", d2.get("cost", 0))
                caller = d2.get("caller", d2.get("model", ""))[:30]
                print(f"    {ts}  ${cost:.5f}  {caller}")
            except:
                print(f"    {l[:80]}")
        break
else:
    print("  cost_log見つからない")

# SES_MailPipeline / SES_MatchingV3 の直近ログ確認
print("\n=== matching_v3 直近ログ ===")
for lp in [base / "matching_v3" / "logs", base / "logs"]:
    if lp.exists():
        logs = sorted(lp.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True)
        if logs:
            newest = logs[0]
            print(f"  {newest.name} ({newest.stat().st_size // 1024}KB)")
            lines = newest.read_text(encoding="utf-8", errors="replace").splitlines()
            for l in lines[-15:]:
                print(f"    {l}")
        break

print("\n=== mail_pipeline 直近ログ ===")
for lp in [base / "mail_pipeline" / "logs", base / "logs"]:
    if lp.exists():
        logs = sorted(lp.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True)
        if logs:
            newest = logs[0]
            lines = newest.read_text(encoding="utf-8", errors="replace").splitlines()
            print(f"  {newest.name}  直近15行:")
            for l in lines[-15:]:
                print(f"    {l}")
        break
