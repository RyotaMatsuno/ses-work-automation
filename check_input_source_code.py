# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

path = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\mail_pipeline.py'
lines = open(path, encoding='utf-8').readlines()
for i, line in enumerate(lines):
    if '入力元' in line or 'input_source' in line.lower() or 'source_label' in line.lower():
        print(f'{i+1}: {line}', end='')
