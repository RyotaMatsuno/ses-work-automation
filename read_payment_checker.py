import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
# payment_checker.pyの先頭部分を確認
with open(r'freee/payment_checker.py', 'r', encoding='utf-8') as f:
    src = f.read()
print(src[:3000])
