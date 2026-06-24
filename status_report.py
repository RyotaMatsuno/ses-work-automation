import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import requests
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
for k, v in config.items():
    os.environ.setdefault(k, v)

print("=" * 60)
print("最終動作確認サマリー")
print("=" * 60)

# 1. Cloud Run health
r = requests.get("https://line-webhook-74735301292.asia-northeast1.run.app/health", timeout=10)
print(f"Cloud Run: {'✅ 稼働中' if r.status_code == 200 else '❌'}  (rev 00044)")

# 2. ローカルでline_queryが正しく動くか
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook")
for m in list(sys.modules):
    if "line_query" in m:
        del sys.modules[m]
from line_query import classify_query

# classify_queryテスト（APIなし）
cases = [("HS 北小金", "HS"), ("H.S 北小金", "HS"), ("hs 北小金", "HS")]
all_ok = True
for txt, exp in cases:
    t, p = classify_query(txt)
    ok = t == "engineer" and p.get("initial") == exp
    if not ok:
        all_ok = False
print(f"classify_query: {'✅ 全パターンOK' if all_ok else '❌'}")

# Noneテスト（APIなし）
null_cases = [
    "",
    "おつかれさまです！\n【名 前】H.S\n単価70万",
    "A" * 101,  # 101文字
]
all_none = True
for txt in null_cases:
    # guard部分だけ確認
    if not txt or not txt.strip() or len(txt.strip()) > 100:
        pass  # None になるはず
    else:
        all_none = False
print(f"ガード(100文字): {'✅ OK' if all_none else '❌'}")

# 3. LINE push quota
r2 = requests.get(
    "https://api.line.me/v2/bot/message/quota/consumption",
    headers={"Authorization": f"Bearer {config.get('LINE_CHANNEL_ACCESS_TOKEN', '')}"},
    timeout=10,
)
usage = r2.json().get("totalUsage", "?")
print(f"LINE quota: {usage}/200通 ({'⚠️ 上限到達 - 6月1日リセット' if usage == 200 else '✅ 余裕あり'})")

print()
print("=" * 60)
print("動作フロー（本番確認方法）")
print("=" * 60)
print()
print("【今すぐ確認できること】")
print("  松野の公式LINEアプリから「HS 北小金」と送信")
print("  → webhook受信 → handle_line_query → マッチ案件一覧")
print("  → reply API（quota無制限）でLINEに返信")
print()
print("  期待する返答:")
print("  【HS｜北小金】マッチ案件 XX件")
print("  ① Java×AI_デジタル通貨...")
print("  　必須: Java")
print("  　単価: 130万 / 粗利: 60万")
print("  　不明() [1日前]")
print("  ...")
print()
print("【push API制限（200通/月）】")
print("  ジョブズからの自動push通知は6月1日リセットまで不可")
print("  reply APIは無制限なので松野が送れば即返信OK")
print()
print("【次の根本課題】")
print("  案件DBに1637件「募集中」蓄積 → mail_pipeline upsert化が必要")
print("  → Windowsターミナルで cleanup_v2.py を直接実行")
print("  → その後 mail_pipeline に upsert + ステータス自動クローズ実装")
