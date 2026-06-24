import json

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\logs\phase0_results.jsonl"

# 最初の3件のキーと内容を表示
with open(path, encoding="utf-8") as f:
    for i, line in enumerate(f):
        if i >= 3:
            break
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        print(f"=== Record {i + 1} ===")
        print(f"  Keys: {list(d.keys())}")
        # 全フィールドを表示（長い値は切り詰め）
        for k, v in d.items():
            sv = str(v)
            if len(sv) > 100:
                sv = sv[:100] + "..."
            print(f"  {k}: {sv}")
        print()
