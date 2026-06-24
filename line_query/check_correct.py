import os
import sys

fpath = os.path.join(os.path.dirname(__file__), "line_query.py")
with open(fpath, "rb") as f:
    raw = f.read()

# 現在ファイルに入っている誤った文字 -> 正しい文字 のbytes置換
fixes = [
    # 務居地 -> 勤務地
    # 務=e58b99, 居=e5b185, 地=e59cb0 -> 勤=e58ba4, 務=e58b99, 地=e59cb0
    (bytes.fromhex("e58b99e5b185e59cb0"), "\u52e4\u52d9\u5730".encode("utf-8")),  # 勤務地
    # 单価（万円） -> 単価（万円）
    # 单=e58d95 -> 単=e58d98
    (bytes.fromhex("e58d95e4bea1efbc88e4b887e58686efbc89"), "\u5358\u4fa1\uff08\u4e07\u5186\uff09".encode("utf-8")),
    # 稼尽可能日 -> 稼働可能日
    # 尽=e5b0bd -> 働=e5838d
    (bytes.fromhex("e7a8bce5b0bde58fafe883bde697a5"), "\u7a3c\u5c3d\u53ef\u80fd\u65e5".encode("utf-8")),
    # 稼尽状況 -> 稼働状況
    (bytes.fromhex("e7a8bce5b0bde78ab6e6b381"), "\u7a3c\u5c3d\u72b6\u6cc1".encode("utf-8")),
]

# 正しいUnicodeを改めて確認
correct = {
    "勤務地": "\u52e4\u52d9\u5730",
    "単価（万円）": "\u5358\u4fa1\uff08\u4e07\u5186\uff09",
    "稼働可能日": "\u7a3c\u5c3d\u53ef\u80fd\u65e5",  # ← これもまだ「稼尽」かも
    "稼働状況": "\u7a3c\u5c3d\u72b6\u6cc1",
}

# 実際のNotionプロパティ名を確認してから置換すべきなので
# まず正しいコードポイントを確認
sys.stdout.buffer.write(b"Correct Unicode check:\n")
for k, v in correct.items():
    sys.stdout.buffer.write(f"  {k}: {v.encode('utf-8').hex()}\n".encode("utf-8"))

# 勤務地 = 勤U+52E4 + 務U+52D9 + 地U+5730
sys.stdout.buffer.write(f"勤務地 hex: {chr(0x52E4) + chr(0x52D9) + chr(0x5730)}".encode("utf-8") + b"\n")
# 単価 = 単U+5358 + 価U+4FA1
sys.stdout.buffer.write(f"単価 hex: {chr(0x5358) + chr(0x4FA1)}".encode("utf-8") + b"\n")
# 稼働 = 稼U+7A3C + 働U+50CD
sys.stdout.buffer.write(f"稼働 hex: {chr(0x7A3C) + chr(0x50CD)}".encode("utf-8") + b"\n")
