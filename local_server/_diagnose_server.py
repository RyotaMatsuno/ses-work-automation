# -*- coding: utf-8 -*-
"""command_server.pyの起動クラッシュ原因を診断するスクリプト"""

import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
LOCAL_SERVER = BASE_DIR / "local_server"

print("=== command_server 起動診断 ===")
print(f"Python: {sys.executable}")
print(f"sys.path: {sys.path[:3]}")

# sys.pathにses_workを追加（command_server.pyと同じ）
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# 1. mail_mcp.mail_rest のimportテスト
print("\n[1] mail_mcp.mail_rest import テスト...")
try:
    print("    OK")
except Exception as e:
    print(f"    NG: {type(e).__name__}: {e}")

# 2. command_server.py全体をサブプロセスで起動してエラー捕捉
# pythonw ではなく python で起動してstderrを捕捉
print("\n[2] command_server.py 起動テスト（5秒タイムアウト）...")
try:
    result = subprocess.run(
        [sys.executable, str(LOCAL_SERVER / "command_server.py")],
        cwd=str(LOCAL_SERVER),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=5,
    )
    print(f"    returncode: {result.returncode}")
    if result.stdout:
        print(f"    stdout: {result.stdout[:500]}")
    if result.stderr:
        print(f"    stderr（クラッシュ原因）:\n{result.stderr[:1000]}")
except subprocess.TimeoutExpired as e:
    # 5秒後もプロセスが生きている = 正常起動
    print("    5秒後も起動中 → 正常起動！（タイムアウトは正常）")
    if e.stdout:
        print(f"    stdout: {e.stdout[:300]}")
except Exception as e:
    print(f"    例外: {type(e).__name__}: {e}")

print("\n=== 診断完了 ===")
