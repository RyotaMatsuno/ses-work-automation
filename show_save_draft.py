# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

path = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\mail_pipeline.py'
lines = open(path, encoding='utf-8').readlines()

# save_draft / save_engineer_draft 関数全体を確認
print('=== save_draft (669行~) ===')
for i in range(668, 780):
    print(f'{i+1}: {lines[i]}', end='')
