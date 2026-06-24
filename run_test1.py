"""
mail_pipeline テスト実行（処理上限1件・タイムアウト対策でサブプロセス起動）
"""

import subprocess
import sys

script = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\mail_pipeline.py"
log = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\pipeline.log"

# PROCESS_LIMITを1件に一時変更して実行
src = open(script, encoding="utf-8").read()
test_src = src.replace("PROCESS_LIMIT = 20", "PROCESS_LIMIT = 1")

test_script = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\mail_pipeline_test1.py"
open(test_script, "w", encoding="utf-8").write(test_src)

print("テストスクリプト生成完了 → バックグラウンド実行開始")
result = subprocess.run(
    [sys.executable, test_script],
    capture_output=True,
    text=True,
    timeout=120,
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline",
)
print("STDOUT:", result.stdout[-2000:] if result.stdout else "(なし)")
print("STDERR:", result.stderr[-500:] if result.stderr else "(なし)")
print("returncode:", result.returncode)
