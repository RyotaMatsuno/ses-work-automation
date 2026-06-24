import os

fpath = os.path.join(os.path.dirname(__file__), "line_query.py")
with open(fpath, "rb") as f:
    raw = f.read()

# hex -> bytes のマッピング（全プロパティキー）
prop_map = {
    bytes.fromhex("e382a4e3838be382b7e383a3e383ab"): "\u30a4\u30cb\u30b7\u30e3\u30eb",  # イニシャル
    bytes.fromhex("e382b9e382ade383ab"): "\u30b9\u30ad\u30eb",  # スキル
    bytes.fromhex("e382b9e38386e383bce382bfe382b9"): "\u30b9\u30c6\u30fc\u30bf\u30b9",  # ステータス
    bytes.fromhex("e383aae383a2e383bce38388"): "\u30ea\u30e2\u30fc\u30c8",  # リモート
    bytes.fromhex("e58299e88083efbc884c494e45e383a1e383a2efbc89"): "\u5099\u8003\uff08LINE\u30e1\u30e2\uff09",
    bytes.fromhex("e58ba4e58b99e59cb0"): "\u52d9\u5c45\u5730",  # 勤務地
    bytes.fromhex("e58d98e4bea1efbc88e4b887e58686efbc89"): "\u5355\u4fa1\uff08\u4e07\u5186\uff09",  # 単価（万円）
    bytes.fromhex("e5908de5898d"): "\u540d\u524d",  # 名前
    bytes.fromhex("e5b09ae58fafe382b9e382ade383ab"): "\u5c1a\u53ef\u30b9\u30ad\u30eb",  # 尚可スキル
    bytes.fromhex("e5bf85e8a681e382b9e382ade383ab"): "\u5fc5\u8981\u30b9\u30ad\u30eb",  # 必要スキル
    bytes.fromhex("e68980e5b19ee4bc9ae7a4be"): "\u6240\u5c5e\u4f1a\u793e",  # 所属会社
    bytes.fromhex("e68b85e5bd93e88085"): "\u62c5\u5f53\u8005",  # 担当者
    bytes.fromhex("e69c80e5af84e3828ae9a785"): "\u6700\u5bc4\u308a\u99c5",  # 最寄り駅
    bytes.fromhex("e69c9fe99693"): "\u671f\u9593",  # 期間
    bytes.fromhex("e6a188e4bbb6e5908d"): "\u6848\u4ef6\u540d",  # 案件名
    bytes.fromhex("e6a188e4bbb6e8a9b3e7b4b0"): "\u6848\u4ef6\u8a73\u7d30",  # 案件詳細
    bytes.fromhex("e7a8bce5838de58fafe883bde697a5"): "\u7a3c\u5c3d\u53ef\u80fd\u65e5",  # 稼働可能日
    bytes.fromhex("e7a8bce5838de78ab6e6b381"): "\u7a3c\u5c3d\u72b6\u6cc1",  # 稼働状況
    bytes.fromhex("e99da2e8ab87e5b88ce69c9b"): "\u9762\u8ac7\u5e0c\u671b",  # 面談希望
}

# ファイル内の化けた文字列（cp932表示）がどう見えるかを把握している
# -> hexが一致するので、raw内のbytesを正しいUTF-8 bytesに置換する
new_raw = raw
for old_bytes, correct_str in prop_map.items():
    correct_bytes = correct_str.encode("utf-8")
    if old_bytes in new_raw:
        new_raw = new_raw.replace(old_bytes, correct_bytes)
        print(f"Replaced: {correct_str}")
    else:
        print(f"NOT FOUND: {correct_str} ({old_bytes.hex()})")

with open(fpath, "wb") as f:
    f.write(new_raw)

print(f"\nDone. {len(raw)} -> {len(new_raw)} bytes")

# 検証
with open(fpath, "rb") as f:
    verify = f.read().decode("utf-8")
print("UTF-8 decode OK")

# engineer_query 内のプロパティキーを再確認
import re as re2

calls = re2.findall(r'_(?:text|select|multi_select|number|date)_prop\([\w]+,\s*["\']([^"\']+)["\']', verify)
print("Keys after fix:")
for c in sorted(set(calls)):
    try:
        c.encode("utf-8")
        print(f"  OK: {c!r}")
    except Exception as e:
        print(f"  NG: {c!r} - {e}")
