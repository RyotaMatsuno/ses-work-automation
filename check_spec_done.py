import sys

sys.stdout.reconfigure(encoding="utf-8")

results = {}

# --- matching_v2.py チェック ---
try:
    with open("matching_v2/matching_v2.py", encoding="utf-8") as f:
        mv2 = f.read()
    results["matching_v2/get_min_gross実装"] = "get_min_gross" in mv2
    results["matching_v2/岡本3万ロジック"] = "'岡本'" in mv2 and "return 3" in mv2
    results["matching_v2/jpholiday"] = "jpholiday" in mv2
    results["matching_v2/is_within_business_days"] = "is_within_business_days" in mv2
    results["matching_v2/案件タイマー廃止確認(timer不在)"] = "timer" not in mv2.lower()
except Exception as e:
    results["matching_v2/READ_ERROR"] = str(e)

# --- mail_pipeline.py チェック ---
try:
    with open("mail_pipeline/mail_pipeline.py", encoding="utf-8") as f:
        mp = f.read()
    results["mail_pipeline/is_within_business_days"] = "is_within_business_days" in mp
    results["mail_pipeline/jpholiday"] = "jpholiday" in mp
    results["mail_pipeline/interview_datetime"] = "interview_datetime" in mp
    results["mail_pipeline/timedelta"] = "timedelta" in mp
except Exception as e:
    results["mail_pipeline/READ_ERROR"] = str(e)

# --- double_check.py チェック ---
import os

dc_paths = [
    "double_check/double_check.py",
]
dc_found = False
for p in dc_paths:
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                dc = f.read()
            results["double_check/get_min_gross使用"] = "get_min_gross" in dc
            results["double_check/岡本閾値分岐"] = "岡本" in dc
            dc_found = True
            break
        except Exception as e:
            results[f"double_check/{p}/READ_ERROR"] = str(e)
if not dc_found:
    results["double_check/FILE_NOT_FOUND"] = True

print("=== チェック結果 ===")
for k, v in results.items():
    status = "OK" if v is True else ("NG" if v is False else f"INFO: {v}")
    print(f"  {k}: {status}")
