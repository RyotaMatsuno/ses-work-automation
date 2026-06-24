import json
import os
import subprocess
import sys
import threading
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def test_mcp_server(name, cmd_args, env_extra=None):
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)

    try:
        proc = subprocess.Popen(
            cmd_args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env
        )
        time.sleep(4)  # 起動待ち

        # initialize送信
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

        def read_stdout():
            while True:
                line = proc.stdout.readline()
                if not line:
                    break
                output.append(line.decode("utf-8", errors="replace").strip())

        t = threading.Thread(target=read_stdout, daemon=True)
        t.start()
        t.join(timeout=5)
        proc.kill()
        _, stderr = proc.communicate()

        stderr_str = stderr.decode("utf-8", errors="replace")

        if output:
            try:
                resp = json.loads(output[0])
                server_info = resp.get("result", {}).get("serverInfo", {})
                return f"✅ OK - {server_info.get('name', '?')} v{server_info.get('version', '?')}"
            except:
                return f"✅ 応答あり: {output[0][:100]}"
        elif "running on stdio" in stderr_str or "running" in stderr_str.lower():
            return f"⚠️ 起動はしたが応答なし - stderr: {stderr_str[:100]}"
        else:
            return f"❌ 起動失敗 - {stderr_str[:200]}"
    except Exception as e:
        return f"❌ エラー: {e}"


npx = r"C:\Program Files\nodejs\npx.cmd"

tests = [
    (
        "memory",
        [npx, "-y", "@modelcontextprotocol/server-memory"],
        {"MEMORY_FILE_PATH": r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mcp_data\memory.json"},
    ),
    ("sequentialthinking", [npx, "-y", "@modelcontextprotocol/server-sequential-thinking"], None),
    ("context7", [npx, "-y", "@upstash/context7-mcp"], None),
]

for name, cmd, env in tests:
    print(f"=== {name} ===")
    result = test_mcp_server(name, cmd, env)
    print(result)
    print()
