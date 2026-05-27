import sys
sys.stdout.reconfigure(encoding='utf-8')

# 1. daily_report.pyを「数字が入っている案件のみ表示」に修正
daily_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\daily_report.py"
with open(daily_path, encoding="utf-8") as f:
    content = f.read()

# 全案件表示→アクティブ案件（どれかが1以上）のみ表示に変更
# build_message関数内でフィルタリングを追加するパッチ
old = "    for project in projects:"
new = """    # 数字が入っている案件のみ表示（全部0は省略）
    active = [p for p in projects if any(p.get(k, 0) or 0 > 0 for k in ["提案中","面談希望","NG","合格","成約"])]
    display_projects = active if active else []
    for project in display_projects:"""

if old in content:
    content = content.replace(old, new, 1)
    with open(daily_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("daily_report.py: フィルタパッチOK")
else:
    # 別のパターンを探す
    import re
    m = re.search(r'for project in projects', content)
    if m:
        print(f"別パターン発見: pos={m.start()}")
        print(content[m.start()-100:m.start()+200])
    else:
        print("パターン見つからない。関数名確認:")
        for i, line in enumerate(content.split('\n')):
            if 'project' in line.lower() and ('for ' in line or 'def ' in line):
                print(f"  {i}: {line}")
