import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import ast

with open(r"freee_auth/token_manager.py", "r", encoding="utf-8") as f:
    src = f.read()
# 関数名だけ抽出
tree = ast.parse(src)
funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
print("関数一覧:", funcs)
print("---先頭200文字---")
print(src[:300])
