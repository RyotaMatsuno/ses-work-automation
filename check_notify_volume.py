import sys

sys.stdout.reconfigure(encoding="utf-8")

# 今月のマッチング結果件数確認
import json
import os

result_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\result.json"
if os.path.exists(result_path):
    with open(result_path, encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("projects", data) if isinstance(data, dict) else data
    total_notifications = 0
    for item in items:
        candidates = item.get("candidates", [])
        # 案件1件につき担当者に1通（松野 or 岡本 or 両方）
        # 最大2通/案件と仮定
        if candidates:
            total_notifications += 2  # 松野+岡本の最大ケース
    print(f"案件数: {len(items) if isinstance(items, list) else '不明'}")
    print(f"最大通知数/回: {total_notifications}通")
    print(f"月4回実行なら: {total_notifications * 4}通")
    print(f"月200通制限に対して: {'OK' if total_notifications * 4 <= 200 else 'NG'}")
else:
    print("result.json: なし")

# schtasks確認
import subprocess

r = subprocess.run(
    ["schtasks", "/query", "/tn", "jobz_matching_daily"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
)
print(f"\nmatching定時タスク:\n{r.stdout.strip()}")
