import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# マッチ案件なし の周辺を cp932 で検索
with open("line_webhook/matching_logic.py", "rb") as f:
    raw = f.read()

target = "マッチ案件なし".encode("cp932")
idx = raw.find(target)
print(f"cp932 idx={idx}")
if idx != -1:
    chunk = raw[max(0, idx - 600) : idx + 800]
    print(chunk.decode("cp932", errors="replace"))

# 全ファイルサイズと行数
lines = raw.decode("cp932", errors="replace").split("\n")
print(f"\nTotal: {len(raw)} bytes, {len(lines)} lines")

# 「案件なし」「no_match」「マッチ」含む行を全抽出（cp932デコード）
content_cp932 = raw.decode("cp932", errors="replace")
for i, line in enumerate(content_cp932.split("\n")):
    if any(kw in line for kw in ["マッチ案件なし", "案件なし", "no_match", "マッチなし", "PH?"]):
        print(f"L{i + 1}: {line}")
