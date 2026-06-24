import json
import sys

try:
    with open("mail_pipeline/processed_ids.json", encoding="utf-8") as f:
        d = json.load(f)
    print(f"型: {type(d)}")
    if isinstance(d, list):
        print(f"件数: {len(d)}")
        print(f"最初5件: {d[:5]}")
    elif isinstance(d, dict):
        print(f"キー数: {len(d)}")
        for k, v in list(d.items())[:3]:
            print(f"  {k}: {str(v)[:100]}")
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
