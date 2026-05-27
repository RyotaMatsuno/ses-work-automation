import sys
sys.stdout.reconfigure(encoding='utf-8')

# composer.pyのテンプレート「所属会社 松野様」部分を実データで埋めるよう修正
composer_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pipeline_v1\composer.py"
with open(composer_path, encoding="utf-8") as f:
    content = f.read()

print("現在のcomposer.py（最初の100行）:")
lines = content.split('\n')
for i, line in enumerate(lines[:100], 1):
    print(f"{i}: {line}")
