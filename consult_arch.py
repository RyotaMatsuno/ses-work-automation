import io
import sys

import anthropic
from dotenv import dotenv_values

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

cfg = dotenv_values("config/.env")
client = anthropic.Anthropic(api_key=cfg["ANTHROPIC_API_KEY"])

prompt = """以下の技術的問題について意見を聞かせてください。

【状況】
PythonのシンプルなHTTPサーバー（command_server.py）でローカルのCLIコマンドを実行するMCPサーバーを運用中。
「codex exec」のような長時間プロセス（2〜5分かかるCLI）を同期実行すると、その間サーバー全体がブロックされてハングします。

【現在の構造】
- Python標準の BaseHTTPRequestHandler ベース
- POST /run でコマンドを受け取り subprocess.run() で同期実行
- レスポンスは実行完了後に返す

【問題】
codex execが2〜5分かかるため、その間jobz-commandサーバーが一切のリクエストを受け付けられない。

【検討中の対策A】
ThreadingHTTPServer に変更し、各リクエストを別スレッドで処理する。

【検討中の対策B】
codex exec専用の別ポート（8766）にサーバーを分離する。

【検討中の対策C】
非同期ジョブキューにする。POST /runで即座にjob_idを返し、クライアントがGET /status/{job_id}でポーリングする。

質問：
1. A・B・Cの中でどれが最も適切か、またその理由
2. 採用案の具体的な実装上の注意点（スレッドセーフ、タイムアウト管理、プロセス管理など）
3. 他に見落としている問題や、より良い対策があれば
4. MCPサーバーとして使う場合の特有の考慮点があれば"""

response = client.messages.create(
    model="claude-opus-4-5", max_tokens=2000, messages=[{"role": "user", "content": prompt}]
)
print(response.content[0].text)
