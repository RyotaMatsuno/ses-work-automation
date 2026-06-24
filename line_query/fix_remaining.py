import os
import sys

fpath = os.path.join(os.path.dirname(__file__), "line_query.py")
with open(fpath, "rb") as f:
    raw = f.read()

# 現在ファイルに入っている誤り -> 正しいbytes
# (Notionの実プロパティ名hexを正解として使用)
fixes = [
    # 務居地(e58b99e5b185e59cb0) -> 勤務地(e58ba4e58b99e59cb0)
    (bytes.fromhex("e58b99e5b185e59cb0"), bytes.fromhex("e58ba4e58b99e59cb0")),
    # 单価（万円）(e58d95...) -> 単価（万円）(e58d98...)
    (bytes.fromhex("e58d95e4bea1efbc88e4b887e58686efbc89"), bytes.fromhex("e58d98e4bea1efbc88e4b887e58686efbc89")),
    # 稼尽可能日(e7a8bce5b0bde58fafe883bde697a5) -> 稼働可能日(e7a8bce5838de58fafe883bde697a5)
    (bytes.fromhex("e7a8bce5b0bde58fafe883bde697a5"), bytes.fromhex("e7a8bce5838de58fafe883bde697a5")),
    # 稼尽状況(e7a8bce5b0bde78ab6e6b381) -> 稼働状況(e7a8bce5838de78ab6e6b381)
    (bytes.fromhex("e7a8bce5b0bde78ab6e6b381"), bytes.fromhex("e7a8bce5838de78ab6e6b381")),
    # 所属会社(e68980e5b19ee4bc9ae7a4be) は正しいのでそのまま
    # 担当者(e68b85e5bd93e88085) は正しい
]

new_raw = raw
for old_b, new_b in fixes:
    if old_b in new_raw:
        new_raw = new_raw.replace(old_b, new_b)
        sys.stdout.buffer.write(b"Fixed: " + new_b + b"\n")
    else:
        sys.stdout.buffer.write(b"NOT FOUND: " + old_b.hex().encode() + b"\n")

with open(fpath, "wb") as f:
    f.write(new_raw)

# 最終検証: 全プロパティキーが正しいか
with open(fpath, "rb") as f:
    verify = f.read().decode("utf-8")

import re

calls = re.findall(r'_(?:text|select|multi_select|number|date)_prop\([\w]+,\s*["\']([^"\']+)["\']', verify)

# Notion実プロパティ名
notion_keys = set(
    [
        "\u6240\u5c5e\u4f1a\u793e\u540d",  # 所属会社名
        "\u62c5\u5f53\u8005",  # 担当者
        "\u7a3c\u5c3d\u72b6\u6cc1",  # 稼働状況
        "\u7a3c\u5c3d\u53ef\u80fd\u65e5",  # 稼働可能日
        "\u30a4\u30cb\u30b7\u30e3\u30eb",  # イニシャル
        "\u30b9\u30ad\u30eb",  # スキル
        "\u6700\u5bc4\u308a\u99c5",  # 最寄り駅
        "\u5358\u4fa1\uff08\u4e07\u5186\uff09",  # 単価（万円）
        "\u540d\u524d",  # 名前
        "\u30b9\u30c6\u30fc\u30bf\u30b9",  # ステータス
        "\u6848\u4ef6\u8a73\u7d30",  # 案件詳細
        "\u9762\u8ac7\u5e0c\u671b",  # 面談希望
        "\u5c1a\u53ef\u30b9\u30ad\u30eb",  # 尚可スキル
        "\u671f\u9593",  # 期間
        "\u5358\u4fa1\uff08\u4e07\u5186\uff09",  # 単価（万円）
        "\u5fc5\u8981\u30b9\u30ad\u30eb",  # 必要スキル
        "\u6848\u4ef6\u540d",  # 案件名
        "\u30ea\u30e2\u30fc\u30c8",  # リモート
        "\u5099\u8003\uff08LINE\u30e1\u30e2\uff09",  # 備考（LINEメモ）
        "\u52e4\u52d9\u5730",  # 勤務地
        "\u6240\u5c5e\u4f1a\u793e",  # 所属会社
    ]
)

sys.stdout.buffer.write(b"\nKey validation:\n")
for c in sorted(set(calls)):
    ok = c in notion_keys
    sys.stdout.buffer.write(f"  {'OK' if ok else 'NG'}: {c}\n".encode("utf-8"))
