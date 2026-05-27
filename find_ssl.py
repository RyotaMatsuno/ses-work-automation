# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

path = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\mail_pipeline.py'
lines = open(path, encoding='utf-8').readlines()
for i, line in enumerate(lines):
    low = line.lower()
    if 'ssl' in low or 'imap4' in low or '.connect' in low or 'certificate' in low:
        if i > 100:
            print(f'{i+1}: {line}', end='')
