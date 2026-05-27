import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
path = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\mail_pipeline.py'
lines = open(path, encoding='utf-8').readlines()
print(f'総行数: {len(lines)}')
print('--- 冒頭100行 ---')
print(''.join(lines[:100]))
