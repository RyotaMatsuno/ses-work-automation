import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
path = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\mail_pipeline.py'
lines = open(path, encoding='utf-8').readlines()
# classify_email関数を探す
for i, line in enumerate(lines):
    if 'classify_email' in line or 'def classify' in line or 'SKIP_PATTERN' in line or 'batch' in line.lower():
        print(f'{i+1}: {line}', end='')
