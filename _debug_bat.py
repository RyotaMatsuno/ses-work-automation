import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# batファイルの中身をバイナリで確認
with open("task_auto_runner/run_auto_runner.bat", "rb") as f:
    raw = f.read()
print("=== run_auto_runner.bat (bytes) ===")
print(raw)
print()
print("=== cp932デコード ===")
print(raw.decode("cp932", errors="replace"))

# 手動でbatを実行してエラーを確認
print("\n=== bat手動実行 ===")
result = subprocess.run(
    ["cmd", "/c", r"task_auto_runner\run_auto_runner.bat"],
    capture_output=True,
    encoding="cp932",
    errors="replace",
    timeout=30,
)
print(f"returncode: {result.returncode}")
print(f"stdout: {result.stdout[:500]}")
print(f"stderr: {result.stderr[:500]}")
