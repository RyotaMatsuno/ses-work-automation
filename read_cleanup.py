
import sys
sys.stdout.reconfigure(encoding='utf-8')

# cleanup_v2.pyの内容確認（再実行前に仕様把握）
with open('cleanup_v2.py', 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()
print(content[:3000])
