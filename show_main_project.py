# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

path = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\mail_pipeline.py'
lines = open(path, encoding='utf-8').readlines()

# メイン処理 780行以降を確認
print('=== main処理 案件部分 (815~880) ===')
for i in range(814, 880):
    print(f'{i+1}: {lines[i]}', end='')
