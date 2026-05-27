# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

path = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\mail_pipeline.py'
content = open(path, encoding='utf-8').read()

old = '''def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\\n")'''

new = '''def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\\n")
    except (PermissionError, OSError):
        pass  # OneDrive同期ロック等でファイルが書けない場合はスキップ'''

if old in content:
    content = content.replace(old, new, 1)
    open(path, 'w', encoding='utf-8').write(content)
    print('OK: log関数を修正しました')
else:
    print('NG: 対象コードが見つかりません')
    # 現在の関数定義を確認
    for i, line in enumerate(content.splitlines()):
        if 'def log(' in line:
            print(f'Line {i+1}: {line}')
