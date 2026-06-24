import base64
import hashlib
import hmac
import io
import json
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import requests
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
MATSUNO_TOKEN = config.get("LINE_CHANNEL_ACCESS_TOKEN")
MATSUNO_SECRET = config.get("LINE_CHANNEL_SECRET", "")
MATSUNO_USER_ID = config.get("MATSUNO_LINE_USER_ID") or "Ue3508b43b84991f5a68281da5bf4cf39"
WEBHOOK_URL = "https://line-webhook-74735301292.asia-northeast1.run.app/webhook"


def post_webhook(text, uid=None):
    uid = uid or MATSUNO_USER_ID
    body = json.dumps(
        {
            "events": [
                {
                    "type": "message",
                    "webhookEventId": f"test_{abs(hash(text))}",
                    "replyToken": "noreply_" + "0" * 32,
                    "source": {"type": "user", "userId": uid},
                    "message": {"type": "text", "text": text, "id": "99999"},
                }
            ]
        }
    ).encode("utf-8")
    sig = base64.b64encode(hmac.new(MATSUNO_SECRET.encode(), body, hashlib.sha256).digest()).decode()
    r = requests.post(
        WEBHOOK_URL, headers={"Content-Type": "application/json", "X-Line-Signature": sig}, data=body, timeout=20
    )
    return r.status_code


def push(text):
    r = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={"Authorization": f"Bearer {MATSUNO_TOKEN}", "Content-Type": "application/json"},
        json={"to": MATSUNO_USER_ID, "messages": [{"type": "text", "text": text}]},
        timeout=10,
    )
    return r.status_code


print("=== 本番統合テスト（webhook経由）===")
push("🔧 ジョブズ: 最終検証テスト開始")
time.sleep(1)

tests = [
    ("HS 北小金", "エンジニア照会①"),
    ("H.S 北小金", "エンジニア照会②（ドット付き）"),
    ("hs 北小金", "エンジニア照会③（小文字）"),
    # スキルシート本文 → classify_message に委ねる（DBに登録する可能性あるので short version）
    ("おつかれさまです！よろしくお願いします", "短文→一致なし→classify_message"),
]

all_200 = True
for text, desc in tests:
    status = post_webhook(text)
    ok = status == 200
    if not ok:
        all_200 = False
    print(f"  {'✅' if ok else '❌'} [{desc}] status={status}")
    time.sleep(0.5)

push(
    f"✅ webhook統合テスト完了 (00041)\n"
    f"全{len(tests)}件 {'OK' if all_200 else 'NG'}\n\n"
    "実際に「HS 北小金」と送ってみてください\n"
    "マッチ案件一覧が返ってきたら完全動作確認です"
)
print(f"\n総合: {'✅ 全200OK' if all_200 else '❌ 失敗あり'}")
