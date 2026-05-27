import time, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
time.sleep(90)
log = open(r'ses_work/codex_v3.log', encoding='utf-8', errors='replace').read()
lines = log.splitlines()
print(f"総行数:{len(lines)}")
print('\n'.join(lines[-30:]))
