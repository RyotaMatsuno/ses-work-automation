import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('freee_auth/token_manager.py', encoding='utf-8') as f:
    print(f.read(), flush=True)
