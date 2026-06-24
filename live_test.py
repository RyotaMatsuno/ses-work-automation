import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import requests
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
MATSUNO_TOKEN = config.get("LINE_CHANNEL_ACCESS_TOKEN")
MATSUNO_USER_ID = config.get("MATSUNO_LINE_USER_ID") or "Ue3508b43b84991f5a68281da5bf4cf39"


def push(text):
    r = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={"Authorization": f"Bearer {MATSUNO_TOKEN}", "Content-Type": "application/json"},
        json={"to": MATSUNO_USER_ID, "messages": [{"type": "text", "text": text}]},
        timeout=15,
    )
    return r.status_code, r.text[:100]


# テスト1: HS 北小金
print("=== 本番テスト1: push「HS 北小金」→ webhookで自分自身に送る ===")
# 注意: push APIでテストするより、実際にLINEから送信する方が正確
# ここではWebhook URLに直接POSTしてテスト
import base64
import hashlib
import hmac
import json

WEBHOOK_URL = "https://line-webhook-74735301292.asia-northeast1.run.app/webhook"
MATSUNO_SECRET = config.get("LINE_CHANNEL_SECRET", "")


def make_test_event(text):
    return {
        "events": [
            {
                "type": "message",
                "webhookEventId": f"test_{abs(hash(text))}",
                "replyToken": "test_reply_token_00000000000",
                "source": {"type": "user", "userId": MATSUNO_USER_ID},
                "message": {"type": "text", "text": text, "id": "99999"},
            }
        ]
    }


def test_webhook(text):
    body = json.dumps(make_test_event(text)).encode("utf-8")
    sig = base64.b64encode(hmac.new(MATSUNO_SECRET.encode("utf-8"), body, hashlib.sha256).digest()).decode("utf-8")
    r = requests.post(
        WEBHOOK_URL, headers={"Content-Type": "application/json", "X-Line-Signature": sig}, data=body, timeout=30
    )
    return r.status_code, r.text[:200]


print("テスト1: HS 北小金")
status, resp = test_webhook("HS 北小金")
print(f"  status={status}, resp={resp}")
print()

print("テスト2: H.S 北小金（ドット付き）")
status, resp = test_webhook("H.S 北小金")
print(f"  status={status}, resp={resp}")
print()

print("テスト3: 長文（スキルシート本文 → classify_messageへ）")
long_text = """おつかれさまです!
うちの社員の林が7月から営業再開になりました。
Web系のJAVA案件ありましたらお願いします！
【名 前】H.S(55歳/男性)
【単 金】70万"""
status, resp = test_webhook(long_text)
print(f"  status={status}, resp={resp}")
print()

print("※テスト後、松野の公式LINEに返信が来れば本番テスト成功")
print("  返信が「一致する案件が見つかりませんでした」でなければ修正成功")
