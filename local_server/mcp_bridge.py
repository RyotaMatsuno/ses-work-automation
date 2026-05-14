"""
ジョブズ用 コマンド実行MCPサーバー
Claude Desktop から使えるMCPツールとして command_server.py に橋渡しする

設定: claude_desktop_config.json に追加が必要
"""

import asyncio
import json
import urllib.request
import urllib.error
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

AUTH_TOKEN = "jobz-terra-2026"
SERVER_URL = "http://127.0.0.1:8765"

app = Server("jobz-command-mcp")


def http_post(endpoint: str, payload: dict, timeout: int = 90) -> dict:
    url = f"{SERVER_URL}{endpoint}"
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Auth-Token": AUTH_TOKEN,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')}"}
    except Exception as e:
        return {"error": str(e)}


@app.list_tools()
async def list_tools():
    return [
        types.Tool(
            name="run_command",
            description="ローカルPCでターミナルコマンドを実行する。Python/bat/pip/git/node等なんでも実行可能。",
            inputSchema={
                "type": "object",
                "properties": {
                    "cmd": {"type": "string", "description": "実行するコマンド（例: python script.py, pip install requests, git push）"},
                    "cwd": {"type": "string", "description": "実行ディレクトリ（省略時はses_work）"},
                    "timeout": {"type": "integer", "description": "タイムアウト秒数（デフォルト60）"},
                },
                "required": ["cmd"],
            },
        ),
        types.Tool(
            name="write_and_run",
            description="ファイルを書き込んでから即実行する。スクリプト作成→実行を1ステップで完結。",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "書き込み先のフルパス"},
                    "content": {"type": "string", "description": "ファイルの内容"},
                    "run_cmd": {"type": "string", "description": "書き込み後に実行するコマンド（省略可）"},
                    "cwd": {"type": "string", "description": "実行ディレクトリ（省略時はses_work）"},
                },
                "required": ["filepath", "content"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "run_command":
        result = http_post("/run", arguments)
        text = json.dumps(result, ensure_ascii=False, indent=2)
        return [types.TextContent(type="text", text=text)]

    elif name == "write_and_run":
        result = http_post("/write_and_run", arguments)
        text = json.dumps(result, ensure_ascii=False, indent=2)
        return [types.TextContent(type="text", text=text)]

    else:
        return [types.TextContent(type="text", text=f"unknown tool: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
