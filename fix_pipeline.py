
import re

fpath = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\mail_pipeline.py'

with open(fpath, 'r', encoding='utf-8') as f:
    content = f.read()

original = content

# 修正1: register_project内の "備考" → "案件詳細"
content = content.replace(
    '"備考": {"rich_text": [{"text": {"content": note[:2000]}}]}',
    '"案件詳細": {"rich_text": [{"text": {"content": note[:2000]}}]}'
)

# 修正2: "必須スキル" → "必要スキル" (register_project内)
content = content.replace(
    'properties["必須スキル"]',
    'properties["必要スキル"]'
)

# 修正3: register_project の return 前にエラーログ挿入
old3 = (
    '        json={"parent": {"database_id": PROJECT_DB}, "properties": properties}\n'
    '    )\n'
    '    return res.status_code == 200\n'
    '\n'
    '\n'
    'def register_engineer'
)
new3 = (
    '        json={"parent": {"database_id": PROJECT_DB}, "properties": properties}\n'
    '    )\n'
    '    if res.status_code != 200:\n'
    '        log(f"  [Notion ERROR project] {res.status_code}: {res.text[:300]}")\n'
    '    return res.status_code == 200\n'
    '\n'
    '\n'
    'def register_engineer'
)
content = content.replace(old3, new3)

# 修正4: register_engineer の return 前にエラーログ挿入
old4 = (
    '        json={"parent": {"database_id": ENGINEER_DB}, "properties": properties}\n'
    '    )\n'
    '    return res.status_code == 200\n'
    '\n'
    '\n'
    'def get_available_engineers'
)
new4 = (
    '        json={"parent": {"database_id": ENGINEER_DB}, "properties": properties}\n'
    '    )\n'
    '    if res.status_code != 200:\n'
    '        log(f"  [Notion ERROR engineer] {res.status_code}: {res.text[:300]}")\n'
    '    return res.status_code == 200\n'
    '\n'
    '\n'
    'def get_available_engineers'
)
content = content.replace(old4, new4)

if content == original:
    print("WARNING: 変更なし - 対象文字列が見つからなかった可能性あり")
else:
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("修正完了")

# 修正確認
checks = [
    ('"案件詳細"' in content, '"案件詳細" に修正済み'),
    ('"必要スキル"' in content, '"必要スキル" に修正済み'),
    ('[Notion ERROR project]' in content, 'register_project エラーログ追加済み'),
    ('[Notion ERROR engineer]' in content, 'register_engineer エラーログ追加済み'),
    ('"備考": {"rich_text"' not in content, '"備考" 残存なし'),
    ('"必須スキル"' not in content, '"必須スキル" 残存なし'),
]
for ok, label in checks:
    print(f"  {'OK' if ok else 'NG'} {label}")
