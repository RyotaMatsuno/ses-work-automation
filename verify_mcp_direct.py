import json
import os
import subprocess
import sys
import threading
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def test_node_direct(name, node_path, script_path, env_extra=None):
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)

    proc = subprocess.Popen(
        [node_path, script_path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env
    )
    time.sleep(2)

    init_msg = (
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1.0"},
                },
            }
        )
        + "\n"
    )
    proc.stdin.write(init_msg.encode())
    proc.stdin.flush()

    output = []

    def read():
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            output.append(line.decode("utf-8", errors="replace").strip())

    t = threading.Thread(target=read, daemon=True)
    t.start()
    t.join(timeout=4)
    proc.kill()
    _, stderr = proc.communicate()

    if output:
        try:
            resp = json.loads(output[0])
            si = resp.get("result", {}).get("serverInfo", {})
            caps = resp.get("result", {}).get("capabilities", {})
            return f"✅ {si.get('name')} v{si.get('version')} | capabilities: {list(caps.keys())}"
        except:
            return f"✅ 応答: {output[0][:150]}"
    else:
        stderr_str = stderr.decode("utf-8", errors="replace")
        return f"❌ 応答なし | stderr: {stderr_str[:150]}"


node = r"C:\Program Files\nodejs\node.exe"
npm_modules = r"C:\Users\ma_py\AppData\Roaming\npm\node_modules"
mem_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mcp_data\memory.json"

tests = [
    (
        "memory",
        os.path.join(npm_modules, r"@modelcontextprotocol\server-memory\dist\index.js"),
        {"MEMORY_FILE_PATH": mem_path},
    ),
    (
        "sequentialthinking",
        os.path.join(npm_modules, r"@modelcontextprotocol\server-sequential-thinking\dist\index.js"),
        None,
    ),
    ("context7", os.path.join(npm_modules, r"@upstash\context7-mcp\dist\index.js"), None),
]

for name, script, env in tests:
    result = test_node_direct(name, node, script, env)
    print(f"{name}: {result}")
