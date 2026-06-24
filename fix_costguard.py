import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

mp = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\mail_pipeline.py")
with open(mp, encoding="utf-8", errors="replace") as f:
    content = f.read()

# get_today_cost_usd の修正
# ts フィールド（ISO datetime）の先頭10文字がdateなので、それで判定する
old = '''def get_today_cost_usd() -> float:
    """usage_tracker/cost_log.jsonl から今日の累計コストを返す"""
    try:
        cost_log = BASE_DIR.parent / "usage_tracker" / "cost_log.jsonl"
        if not cost_log.exists():
            return 0.0
        today = date.today().isoformat()
        total = 0.0
        with open(cost_log, encoding="utf-8") as f:
            for line in f:
                entry = json.loads(line.strip())
                if entry.get("date") == today:
                    total += entry.get("cost_usd", 0.0)
        return total
    except Exception:
        return 0.0'''

new = '''def get_today_cost_usd() -> float:
    """usage_tracker/cost_log.jsonl から今日の累計コストを返す"""
    try:
        cost_log = BASE_DIR.parent / "usage_tracker" / "cost_log.jsonl"
        if not cost_log.exists():
            return 0.0
        today = date.today().isoformat()  # "2026-06-04"
        total = 0.0
        with open(cost_log, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                # dateフィールドまたはtsフィールドの先頭10文字で判定
                entry_date = entry.get("date") or (entry.get("ts", "")[:10])
                if entry_date == today:
                    total += entry.get("cost_usd", 0.0)
        return total
    except Exception:
        return 0.0'''

if old in content:
    content = content.replace(old, new)
    with open(mp, "w", encoding="utf-8") as f:
        f.write(content)
    print("修正完了")
else:
    print("NG: 対象箇所が見つからない。現在の関数を表示します")
    start = content.find("def get_today_cost_usd")
    print(content[start : start + 600])
