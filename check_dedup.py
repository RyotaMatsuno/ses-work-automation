import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# 重複案件の先頭40文字を確認
names = [
    "Java×AI_デジタル通貨・ブロックチェーン企業",
    "Java×AI_デジタル通貨・ブロックチェーン企",
    "Java×AI_デジタル通貨・ブロックチェーン企業向けシステム開発",
]
for n in names:
    print(f"全長: {len(n)} 先頭40: [{n[:40]}]")

print()
print("→ 先頭40文字が全部違うので dedup では排除できない")
print("→ これは意図的に別案件として登録されているか、名前の表記揺れ")
print()
print("解決策: 先頭25文字でdedup（SES案件名は最初の25文字で一意になるケースが多い）")

for n in names:
    print(f"先頭25: [{n[:25]}]")
