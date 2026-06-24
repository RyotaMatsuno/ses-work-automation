import sys

sys.stdout.reconfigure(encoding="utf-8")
import os

lw = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook"
lq_path = os.path.join(lw, "line_query.py")
with open(lq_path, encoding="utf-8") as f:
    content = f.read()
    lines = content.split("\n")

# engineer_query の重複除去ロジック確認
print("=== 現在の重複除去ロジック (L325-360) ===")
in_block = False
for i, line in enumerate(lines, 1):
    if "# dedup" in line or "dedup" in line.lower() or "_seen" in line or "_deduped" in line:
        in_block = True
    if in_block:
        print(f"L{i}: {line}")
        if in_block and i > 5 and "projects = _deduped" in line:
            break

# 現在: 先頭20文字で重複除去
# 問題: "Java×AI_デジタル通貨・ブロックチェーン企業" の先頭20文字が違うと重複と判定されない
# "Java×AI_デジタル通貨・ブロックチェーン企業向けシステム開発" と "Java×AI_デジタル通貨・ブロックチェーン企" は先頭20文字が同じ？
# 確認
names = [
    "Java×AI_デジタル通貨・ブロックチェーン企業",
    "Java×AI_デジタル通貨・ブロックチェーン企業向けシステム開発",
    "Java×AI_デジタル通貨・ブロックチェーン企",
    "Claude Codeを用いた開発案件",
    "大手インターネット事業会社でのフロントエンド開発",
]
print("\n=== 先頭20文字での重複チェック ===")
seen = set()
for name in names:
    k = name[:20]
    dup = k in seen
    seen.add(k)
    print(f"  {'DUP' if dup else 'NEW'}: {name!r} -> key={k!r}")
