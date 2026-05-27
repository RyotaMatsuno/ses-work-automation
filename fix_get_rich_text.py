# -*- coding: utf-8 -*-
import sys, io, shutil
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

p2 = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\matching_v2.py'
bak = p2 + '.bak_pfix'
shutil.copy2(p2, bak)
print(f'backup: {bak}')

content = open(p2, encoding='utf-8').read()

old = '''def get_rich_text(props, key):
    items = props.get(key, {}).get("rich_text", [])
    return items[0]["plain_text"] if items else ""'''

new = '''def get_rich_text(props, key):
    items = props.get(key, {}).get("rich_text", [])
    return "".join(item.get("plain_text", "") for item in items)'''

if old in content:
    content = content.replace(old, new, 1)
    open(p2, 'w', encoding='utf-8').write(content)
    print('OK: get_rich_text() を全ブロック結合に修正')
else:
    print('NG: パターンが見つかりません')
    # 現在の関数確認
    for i, line in enumerate(content.splitlines()):
        if 'def get_rich_text' in line:
            print(f'Line {i+1}: {line}')
