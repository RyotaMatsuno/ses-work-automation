import json
import os
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# memory MCPサーバーをstdioモードで起動してみる（実際にClaudeと同じ条件）
env = os.environ.copy()
env["MEMORY_FILE_PATH"] = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mcp_data\memory.json"

proc = subprocess.Popen(
    [r"C:\Program Files\nodejs\npx.cmd", "-y", "@modelcontextprotocol/server-memory"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    env=env,
)

# MCPのinitializeメッセージを送信
init_msg = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}},
}
msg_str = json.dumps(init_msg)
content = f"Content-Length: {len(msg_str)}\r\n\r\n{msg_str}"
proc.stdin.write(content.encode())
proc.stdin.flush()

time.sleep(3)

try:
    proc.stdin.close()
    stdout, stderr = proc.communicate(timeout=5)
    print("=== STDOUT ===")
    print(stdout.decode("utf-8", errors="replace")[:2000])
    print("=== STDERR ===")
    print(stderr.decode("utf-8", errors="replace")[:1000])
except subprocess.TimeoutExpired:
    proc.kill()
    stdout, stderr = proc.communicate()
    print("=== STDOUT (timeout) ===")
    print(stdout.decode("utf-8", errors="replace")[:2000])
    print("=== STDERR (timeout) ===")
    print(stderr.decode("utf-8", errors="replace")[:1000])
