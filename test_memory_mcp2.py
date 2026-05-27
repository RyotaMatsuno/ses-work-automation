import subprocess, os, sys, time, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

env = os.environ.copy()
env["MEMORY_FILE_PATH"] = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mcp_data\memory.json"

proc = subprocess.Popen(
    [r"C:\Program Files\nodejs\npx.cmd", "-y", "@modelcontextprotocol/server-memory"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    env=env
)

time.sleep(3)  # 起動待ち

# MCPのinitializeメッセージ（改行区切り形式でも試す）
init_msg = json.dumps({
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1.0"}
    }
}) + "\n"

proc.stdin.write(init_msg.encode())
proc.stdin.flush()

time.sleep(2)

# 非ブロッキングで読む
import threading

output = []
def read_stdout():
    while True:
        line = proc.stdout.readline()
        if not line:
            break
        output.append(line.decode('utf-8', errors='replace'))

t = threading.Thread(target=read_stdout)
t.daemon = True
t.start()
t.join(timeout=4)

print("=== MCP応答 ===")
print('\n'.join(output) if output else "応答なし（タイムアウト）")

proc.kill()
_, stderr = proc.communicate()
print("=== STDERR ===")
print(stderr.decode('utf-8', errors='replace'))
