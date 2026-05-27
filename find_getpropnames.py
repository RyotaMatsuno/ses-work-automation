# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

path = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\mail_pipeline.py'
lines = open(path, encoding='utf-8').readlines()
# get_database_property_names 関数を探す
for i, line in enumerate(lines):
    if 'get_database_property_names' in line:
        print(f'{i+1}: {line}', end='')
