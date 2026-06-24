import sys
sys.stdout.reconfigure(encoding='utf-8')
import os, subprocess

# 1. Cloud RunのデプロイステータスとRevision確認
# git logで最新コミットを確認
lw = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook'
r = subprocess.run(['git', 'log', '--oneline', '-5'], cwd=lw, capture_output=True, text=True)
print("=== git log ===")
print(r.stdout)

# 2. ローカルのline_query.pyで実際の修正箇所を直接確認
lq_path = os.path.join(lw, 'line_query.py')
with open(lq_path, encoding='utf-8') as f:
    content = f.read()
    lines = f.readlines() if False else content.split('\n')

# _match_station の return False が入っているか
has_fix3 = 'return False  # station specified but no matching station data' in content
has_fix2 = "GROSS_THRESHOLDS.get(assignee, 5)" in content
has_fix1 = 'if line.startswith(_num_label(1))' in content

print(f"BUG-1 (_limit_reply動的化): {'✅' if has_fix1 else '❌'}")
print(f"BUG-2 (threshold default=5): {'✅' if has_fix2 else '❌'}")
print(f"BUG-3 (_match_station=False): {'✅' if has_fix3 else '❌'}")

# 3. Dockerfileを確認（Cloud Runがどのファイルを使っているか）
dockerfile = os.path.join(lw, 'Dockerfile')
if os.path.exists(dockerfile):
    with open(dockerfile, encoding='utf-8') as f:
        print("\n=== Dockerfile ===")
        print(f.read())

# 4. 実際にline_query.pyをローカル実行してHS北小金の結果を確認
# （Notionへの実際のクエリを実行）
print("\n=== ローカルテスト: HS 北小金 ===")
r2 = subprocess.run(
    ['python', '-c', '''
import sys
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook")
from line_query import handle_line_query
result = handle_line_query("HS 北小金")
print(result if result else "(no result)")
'''],
    capture_output=True, text=True, encoding='utf-8',
    cwd=lw
)
print(r2.stdout[:3000])
if r2.stderr:
    print("STDERR:", r2.stderr[:500])
