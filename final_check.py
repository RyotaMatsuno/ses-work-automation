
import sys, subprocess
sys.stdout.reconfigure(encoding='utf-8')

with open('cleanup_v2_new.log', 'r', encoding='cp932', errors='replace') as f:
    lines = f.readlines()

print(f"ログ行数: {len(lines)}")
print("末尾5行:")
print("".join(lines[-5:]))

for line in reversed(lines):
    if '進捗' in line or '完了' in line or '削除完了' in line:
        print(f"最新: {line.strip()}")
        break

result = subprocess.run(['tasklist', '/fi', 'PID eq 13612', '/fo', 'csv'],
                       capture_output=True, text=True, encoding='cp932')
if 'python.exe' in result.stdout:
    print("プロセス: 稼働中")
else:
    print("プロセス: 終了済み")
