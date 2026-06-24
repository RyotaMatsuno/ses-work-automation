import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import base64
import hashlib
import hmac
import json
import time

import requests
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
MATSUNO_TOKEN = config.get("LINE_CHANNEL_ACCESS_TOKEN")
MATSUNO_SECRET = config.get("LINE_CHANNEL_SECRET", "")
MATSUNO_USER_ID = config.get("MATSUNO_LINE_USER_ID") or "Ue3508b43b84991f5a68281da5bf4cf39"
OKAMOTO_TOKEN = config.get("LINE_OKAMOTO_CHANNEL_TOKEN") or config.get("OKAMOTO_LINE_CHANNEL_ACCESS_TOKEN")
OKAMOTO_USER_ID = config.get("OKAMOTO_LINE_USER_ID") or "Uac1d23408573586affa37577c4e2b2ab"

WEBHOOK_URL = "https://line-webhook-74735301292.asia-northeast1.run.app/webhook"


def make_event(text, user_id):
    return {
        "events": [
            {
                "type": "message",
                "webhookEventId": f"finaltest_{abs(hash(text + user_id))}",
                "replyToken": "noreply_00000000000000000000000000000000",
                "source": {"type": "user", "userId": user_id},
                "message": {"type": "text", "text": text, "id": "99999"},
            }
        ]
    }


def webhook_test(text, user_id=None):
    if user_id is None:
        user_id = MATSUNO_USER_ID
    body = json.dumps(make_event(text, user_id)).encode("utf-8")
    sig = base64.b64encode(hmac.new(MATSUNO_SECRET.encode("utf-8"), body, hashlib.sha256).digest()).decode("utf-8")
    r = requests.post(
        WEBHOOK_URL, headers={"Content-Type": "application/json", "X-Line-Signature": sig}, data=body, timeout=30
    )
    return r.status_code


def push_to_matsuno(text):
    r = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={"Authorization": f"Bearer {MATSUNO_TOKEN}", "Content-Type": "application/json"},
        json={"to": MATSUNO_USER_ID, "messages": [{"type": "text", "text": text}]},
        timeout=15,
    )
    return r.status_code


print("=== 最終統合テスト ===")
print()

# テスト通知をLINEに送信
push_to_matsuno("🔧 ジョブズ: LINE照会システム修正完了テスト中...")
time.sleep(1)

# テスト1: HS 北小金（実際のフロー）
print("テスト1: HS 北小金 → webhookに送信")
s = webhook_test("HS 北小金")
print(f"  status={s}")
time.sleep(2)

# テスト2: H.S 北小金（ドット付き）
print("テスト2: H.S 北小金 → webhookに送信")
s = webhook_test("H.S 北小金")
print(f"  status={s}")
time.sleep(2)

# テスト3: 長文スキルシート（Noneでスルーされるはず）
print("テスト3: 長文スキルシート → webhookに送信（「HS 北小金」照会には応答なし = 正常）")
long_text = """おつかれさまです!\nWeb系のJAVA案件ありましたらお願いします!\n長期案件、リモート併用希望です。\n【名 前】H.S(55歳/男性)\n【最寄駅】北小金駅"""
s = webhook_test(long_text)
print(f"  status={s}")
time.sleep(1)

push_to_matsuno(
    "✅ テスト送信完了\n"
    "上記3件のwebhookテストを実行しました\n\n"
    "【期待する動作】\n"
    "テスト1: 「HS｜北小金 マッチ案件○件」が返ってくる\n"
    "テスト2: 同上\n"
    "テスト3: 反応なし（長文スルー）\n\n"
    "松野さんが実際にLINEから「HS 北小金」と送れば本番動作確認できます"
)

print()
print("✅ テスト完了。松野の公式LINEをご確認ください。")
print("  「HS 北小金」への応答が来れば修正成功")
print("  ※replyTokenはダミーなので自動返信は届かない場合あり")
print("  ※実際にLINEアプリから「HS 北小金」と打てば本番テスト完了")
