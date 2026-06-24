# Cloud RunログからMATSUNO_LINE_USER_IDを取得するスクリプト
import re
import subprocess

result = subprocess.run(
    [
        "gcloud",
        "logging",
        "read",
        'resource.type=cloud_run_revision AND resource.labels.service_name=line-webhook AND textPayload:"[userId-matsuno]"',
        "--limit=5",
        "--format=value(textPayload)",
        "--project=ses-work-automation",
    ],
    capture_output=True,
    text=True,
    timeout=30,
)

print("STDOUT:", result.stdout)
print("STDERR:", result.stderr[:200])
print("RC:", result.returncode)

# ユーザーIDをパース
matches = re.findall(r"\[userId-matsuno\]\s*(U[a-f0-9]+)", result.stdout)
if matches:
    uid = matches[0]
    print(f"\n✅ 松野のLINE USER ID発見: {uid}")
else:
    print("\n⚠️ まだLINEメッセージが届いていません。松野さんがLINEを送ると取得できます。")
