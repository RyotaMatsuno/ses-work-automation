
import os, ast

base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
nw = os.path.join(base, "mail_attachment_importer", "notion_writer.py")
with open(nw, encoding="utf-8") as f:
    content = f.read()

# 公開関数を列挙
tree = ast.parse(content)
funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
print("Functions:", funcs)

# 先頭100行を表示
lines = content.split('\n')
for i, l in enumerate(lines[:30]):
    print(f"{i+1}: {l}")
