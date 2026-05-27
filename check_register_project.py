# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# mail_pipeline.pyのregister_project()でraw_bodyをどこに書いているか確認
p1 = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\mail_pipeline.py'
lines = open(p1, encoding='utf-8').readlines()
for i in range(534, 565):
    print(f'{i+1}: {lines[i]}', end='')
