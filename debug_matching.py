import sys

sys.stdout.reconfigure(encoding="utf-8")
import json
import os

# matching_v2の結果ファイルと関連スクリプトを確認
ses = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"

# result.jsonを確認
result_path = os.path.join(ses, "matching_v2", "result.json")
if os.path.exists(result_path):
    with open(result_path, encoding="utf-8") as f:
        data = json.load(f)
    print(f"result.json: {len(data)} records")
    # H.S関連のマッチング結果を確認
    for item in data[:3]:
        print(json.dumps(item, ensure_ascii=False, indent=2)[:500])
        print("---")
else:
    print("result.json not found")

# notify_line.pyの表示ロジック確認
notify_path = os.path.join(ses, "matching_v2", "notify_line.py")
if os.path.exists(notify_path):
    with open(notify_path, encoding="utf-8") as f:
        lines = f.readlines()
    print(f"\nnotify_line.py: {len(lines)} lines")
    # 表示件数制限・粗利計算部分を探す
    for i, line in enumerate(lines, 1):
        if any(
            kw in line
            for kw in ["上位", "top", "limit", "5件", "gross", "粗利", "margin", "profit", "slice", "[:5]", "[:3]"]
        ):
            print(f"L{i}: {line.rstrip()}")
