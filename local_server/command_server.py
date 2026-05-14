"""
ジョブズ用 ローカルコマンド実行サーバー
- localhost:8765 でHTTPリクエストを受け付ける
- ジョブズ（Claude）がFilesystem MCPまたはHTTP経由でコマンドを送信 → PC上で実行 → 結果を返す
- セキュリティ: localhostのみ受付、トークン認証あり
"""

import http.server
import json
import subprocess
import os
import sys
import logging
from datetime import datetime

# ========== 設定 ==========
PORT = 8765
AUTH_TOKEN = "jobz-terra-2026"
LOG_FILE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\local_server\server.log"
# ==========================

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class CommandHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        logger.info(f"{self.address_string()} - {format % args}")

    def send_json(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def check_auth(self):
        token = self.headers.get("X-Auth-Token", "")
        return token == AUTH_TOKEN

    def do_GET(self):
        if self.path == "/health":
            self.send_json(200, {
                "status": "ok",
                "server": "jobz-command-server",
                "time": datetime.now().isoformat()
            })
        else:
            self.send_json(404, {"error": "not found"})

    def do_POST(self):
        # localhost以外は拒否
        if self.client_address[0] not in ("127.0.0.1", "::1"):
            self.send_json(403, {"error": "forbidden: localhost only"})
            return

        # 認証チェック
        if not self.check_auth():
            self.send_json(401, {"error": "unauthorized: invalid token"})
            return

        # ボディ読み込み
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        try:
            req = json.loads(body)
        except json.JSONDecodeError:
            self.send_json(400, {"error": "invalid JSON"})
            return

        path = self.path

        # ========== /run : コマンド実行 ==========
        if path == "/run":
            cmd = req.get("cmd", "")
            cwd = req.get("cwd", r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
            timeout = req.get("timeout", 60)

            if not cmd:
                self.send_json(400, {"error": "cmd is required"})
                return

            logger.info(f"[RUN] cmd={cmd} cwd={cwd}")
            try:
                result = subprocess.run(
                    cmd,
                    shell=True,
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=timeout,
                )
                self.send_json(200, {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                    "cmd": cmd,
                })
            except subprocess.TimeoutExpired:
                self.send_json(408, {"error": f"timeout after {timeout}s", "cmd": cmd})
            except Exception as e:
                self.send_json(500, {"error": str(e), "cmd": cmd})

        # ========== /write_and_run : ファイル書き込み → 実行 ==========
        elif path == "/write_and_run":
            filepath = req.get("filepath", "")
            content = req.get("content", "")
            run_cmd = req.get("run_cmd", "")
            cwd = req.get("cwd", r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")

            if not filepath or not content:
                self.send_json(400, {"error": "filepath and content are required"})
                return

            try:
                os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                logger.info(f"[WRITE] {filepath}")

                result_data = {"filepath": filepath, "written": True}

                if run_cmd:
                    logger.info(f"[RUN after write] {run_cmd}")
                    result = subprocess.run(
                        run_cmd, shell=True, cwd=cwd,
                        capture_output=True, text=True,
                        encoding="utf-8", errors="replace", timeout=120,
                    )
                    result_data.update({
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "returncode": result.returncode,
                    })

                self.send_json(200, result_data)
            except Exception as e:
                self.send_json(500, {"error": str(e)})

        else:
            self.send_json(404, {"error": f"unknown endpoint: {path}"})


def run():
    logger.info(f"ジョブズ コマンドサーバー起動 → localhost:{PORT}")
    logger.info(f"認証トークン: {AUTH_TOKEN}")
    server = http.server.HTTPServer(("127.0.0.1", PORT), CommandHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("サーバー停止")
        server.shutdown()


if __name__ == "__main__":
    run()
