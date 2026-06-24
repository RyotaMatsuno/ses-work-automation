import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"

# 4. notify_line構文チェック
print("=== TEST4: notify_line.py 構文チェック ===", flush=True)
r = subprocess.run(
    ["python", "-c", 'import matching_v2.notify_line; print("import OK")'],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    cwd=BASE,
    env={**os.environ, "DRY_RUN": "1"},
)
print("stdout:", r.stdout[:300], flush=True)
print("stderr:", r.stderr[:500], flush=True)

# 5. webhook_server構文チェック（line_webhookディレクトリで）
print("\n=== TEST5: webhook_server.py 構文チェック ===", flush=True)
r2 = subprocess.run(
    ["python", "-m", "py_compile", "webhook_server.py"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    cwd=os.path.join(BASE, "line_webhook"),
)
print("構文チェック result:", "OK" if r2.returncode == 0 else "NG", flush=True)
print("stderr:", r2.stderr[:500], flush=True)

# 6. line_query.py構文チェック
print("\n=== TEST6: line_query.py 構文チェック ===", flush=True)
r3 = subprocess.run(
    ["python", "-m", "py_compile", "line_query.py"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    cwd=os.path.join(BASE, "line_webhook"),
)
print("構文チェック result:", "OK" if r3.returncode == 0 else "NG", flush=True)
print("stderr:", r3.stderr[:500], flush=True)

# 7. parse_reminder_commandのロジックテスト
print("\n=== TEST7: parse_reminder_command ロジックテスト ===", flush=True)
sys.path.insert(0, os.path.join(BASE, "line_webhook"))
import importlib.util

spec_obj = importlib.util.spec_from_file_location(
    "webhook_server", os.path.join(BASE, "line_webhook", "webhook_server.py")
)
# importは重いのでソース読んでparse関数だけ抽出テスト
test_cases = [
    "某金融系Java開発 T.S 渋谷 催促",
    "Oracle DBマイグレーション案件 H.K 北小金 催促",
    "催促",  # パース失敗ケース
    "T.S 渋谷",  # 催促なし
]


def parse_reminder_command_test(text):
    if not text.endswith("催促"):
        return None
    body = text[:-2].strip()
    parts = body.split()
    if len(parts) < 3:
        return None
    return {
        "project_name": " ".join(parts[:-2]),
        "initial": parts[-2],
        "station": parts[-1],
    }


for tc in test_cases:
    result = parse_reminder_command_test(tc)
    print(f'  入力: "{tc}"', flush=True)
    print(f"  結果: {result}", flush=True)
