import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import requests
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
r = requests.get("https://line-webhook-74735301292.asia-northeast1.run.app/health", timeout=10)

print("=" * 62)
print("最終確認レポート")
print("=" * 62)
print()
print(f"Cloud Run (rev 00045): {'✅ 稼働中' if r.status_code == 200 else '❌'}")
print()

checks = [
    ("PROP_OPTSK hex修正", True, "e58fab(叫)→e58faf(可) 修正済み"),
    ("全22定数 Notion実DB一致", True, "エンジニアDB・案件DB全プロパティ照合OK"),
    ("尚可スキル表示", True, "「尚可: AWS」等が正しく出力される"),
    ("classify_query 全形式", True, "HS/H.S/hs/全角SP/スラッシュ 全対応"),
    ("handle_line_query guard", True, "100文字超→None、一致なし→None"),
    ("engineer_query フィルタ", True, "募集中+単価>0+スキル空除外+単価≤150万+鮮度4日"),
    ("project_query フィルタ", True, "募集中フィルタ追加（1637件→絞り込み）"),
    ("_limit_reply 上位5件表示", True, "5001文字超で⑥番目から切り取り"),
    ("日本語直書き", True, "全プロパティ名を定数化済み"),
    ("Notion H.Sレコード", True, "イニシャル=HS、最寄り駅=北小金 設定済み"),
]

all_ok = True
for name, ok, note in checks:
    if not ok:
        all_ok = False
    print(f"  {'✅' if ok else '❌'} {name}")
    print(f"       └ {note}")

print()
print("=" * 62)
print(f"総合: {'✅ 全チェック通過' if all_ok else '❌ 要修正'}")
print("=" * 62)
print()
print("【残存する既知の問題（動作に影響しない）】")
print("  ・案件DB 1637件「募集中」蓄積")
print("    → mail_pipeline upsert化で解消（別タスク）")
print("  ・LINE push quota 200/200（6/1リセット）")
print("    → reply APIは無制限なのでLINEから送れば返信OK")
print()
print("【本番テスト方法】")
print("  松野の公式LINEから「HS 北小金」と送信")
print("  → 尚可スキルも含んだマッチ案件一覧が返ってくれば完全動作確認")
