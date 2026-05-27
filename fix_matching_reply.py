
# webhook_server.pyのbuild_matching_result_reply()を修正する
import re

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

# 旧コード（items取得部分）を修正
old = '    items = data.get("projects", []) if isinstance(data, dict) else data'
new = '    items = data if isinstance(data, list) else data.get("projects", [])'

if old not in content:
    print("対象コードが見つかりません。現在の該当行を確認します。")
    for i, line in enumerate(content.split('\n')):
        if 'items = data' in line or 'projects' in line.lower() and 'items' in line:
            print(f"L{i+1}: {line}")
else:
    content = content.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("修正完了")

# 修正後の確認
with open(path, encoding="utf-8") as f:
    content2 = f.read()
import ast
ast.parse(content2)
print("構文チェックOK")
