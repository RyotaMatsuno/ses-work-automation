import os
import subprocess
import sys

import requests

sys.stdout.reconfigure(encoding="utf-8")
from dotenv import dotenv_values

cfg = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
API_KEY = cfg.get("NOTION_API_KEY", "")
ENG_DB = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"
PRJ_DB = "343450ff-37c0-81e4-934e-f25f90284a3c"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}
SES = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"

results = {}

# --- 1. エンジニアDB件数 ---
r = requests.post(
    f"https://api.notion.com/v1/databases/{ENG_DB}/query", headers=HEADERS, json={"page_size": 1}, timeout=15
)
eng_count_check = r.status_code == 200
pages = r.json()
# 全件取得
all_eng = []
payload = {"page_size": 100}
while True:
    r2 = requests.post(f"https://api.notion.com/v1/databases/{ENG_DB}/query", headers=HEADERS, json=payload, timeout=30)
    d = r2.json()
    all_eng.extend(d.get("results", []))
    if not d.get("has_more"):
        break
    payload["start_cursor"] = d["next_cursor"]
results["エンジニアDB総件数"] = len(all_eng)

# H.S重複チェック
hs_count = sum(
    1 for p in all_eng if p["properties"].get("名前", {}).get("title", [{}])[0].get("plain_text", "") == "H.S"
)
results["H.S残存件数（1が正常）"] = hs_count

# 稼働可能件数
active = sum(1 for p in all_eng if p["properties"].get("稼働状況", {}).get("select", {}).get("name", "") == "稼働可能")
results["稼働可能エンジニア数"] = active

# --- 2. 案件DB接続確認 ---
r3 = requests.post(
    f"https://api.notion.com/v1/databases/{PRJ_DB}/query", headers=HEADERS, json={"page_size": 1}, timeout=15
)
results["案件DB接続"] = "OK" if r3.status_code == 200 else f"NG({r3.status_code})"

# --- 3. matching_v2.py構文チェック ---
r4 = subprocess.run([sys.executable, "-m", "py_compile", "matching_v2/matching_v2.py"], capture_output=True, cwd=SES)
results["matching_v2.py構文"] = "OK" if r4.returncode == 0 else f"NG: {r4.stderr.decode('utf-8', 'replace')[:100]}"

# --- 4. ロジックテスト ---
r5 = subprocess.run(
    [
        sys.executable,
        "-c",
        "import sys; sys.path.insert(0,'matching_v2');"
        "from matching_v2 import get_min_gross, is_within_business_days;"
        "assert get_min_gross('岡本','松野')==3;"
        "assert get_min_gross('松野','松野')==5;"
        "assert is_within_business_days('2020-01-01T00:00:00.000Z',n=4)==False;"
        "assert is_within_business_days('',n=4)==True;"
        "assert is_within_business_days('2020-01-01',n=4,interview_datetime='2026-06-01')==True;"
        "print('OK')",
    ],
    capture_output=True,
    cwd=SES,
    encoding="utf-8",
    errors="replace",
)
results["粗利/有効期限ロジック"] = r5.stdout.strip() if r5.returncode == 0 else f"NG: {r5.stderr[:100]}"

# --- 5. jpholiday確認 ---
try:
    import jpholiday

    results["jpholidayインストール"] = "OK"
except ImportError:
    results["jpholidayインストール"] = "NG（未インストール）"

# --- 6. mail_pipeline.py構文 ---
r6 = subprocess.run(
    [sys.executable, "-m", "py_compile", "mail_pipeline/mail_pipeline.py"], capture_output=True, cwd=SES
)
results["mail_pipeline.py構文"] = "OK" if r6.returncode == 0 else f"NG: {r6.stderr.decode('utf-8', 'replace')[:100]}"

# --- 7. double_check.py構文 ---
dc_path = os.path.join(SES, "double_check", "double_check.py")
if os.path.exists(dc_path):
    r7 = subprocess.run([sys.executable, "-m", "py_compile", dc_path], capture_output=True, cwd=SES)
    results["double_check.py構文"] = "OK" if r7.returncode == 0 else f"NG: {r7.stderr.decode('utf-8', 'replace')[:100]}"
else:
    results["double_check.py"] = "FILE NOT FOUND"

# --- 8. .env必須キー ---
required_keys = ["NOTION_API_KEY", "NOTION_ENGINEER_DB_ID", "ANTHROPIC_API_KEY", "LINE_CHANNEL_ACCESS_TOKEN"]
for k in required_keys:
    results[f".env/{k}"] = "OK" if cfg.get(k) else "NG（未設定）"

# --- 9. watchdog/タスクスケジューラ確認 ---
r8 = subprocess.run(
    ["schtasks", "/query", "/TN", "mail_pipeline", "/FO", "LIST"],
    capture_output=True,
    cwd=SES,
    encoding="utf-8",
    errors="replace",
)
results["タスクスケジューラ/mail_pipeline"] = "OK" if r8.returncode == 0 else "NG（未登録）"

print("=" * 55)
print("最終チェック結果")
print("=" * 55)
for k, v in results.items():
    icon = "✅" if str(v) in ("OK", "1") or (isinstance(v, int) and v > 0) else "❌" if "NG" in str(v) else "ℹ️"
    print(f"  {icon} {k}: {v}")
print("=" * 55)
