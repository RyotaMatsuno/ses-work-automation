"""
ジョブズ用 ローカルコマンド実行サーバー
- localhost:8765 でHTTPリクエストを受け付ける
- ジョブズ（Claude）がFilesystem MCPまたはHTTP経由でコマンドを送信 → PC上で実行 → 結果を返す
- セキュリティ: localhostのみ受付、トークン認証あり
- v2: ThreadingHTTPServer化（長時間コマンドでブロックしない）
- v2: timeout上限3600秒（1時間）、/write_and_runもtimeoutをリクエストから受け取る
- v3: /run_bg エンドポイント追加（非同期実行 + ログファイル書き出し）
"""

import http.server
import json
import subprocess
import os
import sys
import logging
import threading
from datetime import datetime
from socketserver import ThreadingMixIn

# ========== 設定 ==========
PORT = 8765
AUTH_TOKEN = "jobz-terra-2026"
LOG_FILE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\local_server\server.log"
BG_LOG_DIR = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\local_server\bg_logs"
MAX_TIMEOUT = 3600  # 上限1時間
# ==========================

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
os.makedirs(BG_LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# バックグラウンドジョブ管理
bg_jobs = {}  # job_id -> {status, log_file, pid, start_time}
bg_jobs_lock = threading.Lock()


def run_bg_job(job_id, cmd, cwd, log_file):
    """バックグラウンドでコマンドを実行し、ログをファイルに書き出す"""
    try:
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(f"[START] {datetime.now().isoformat()}\n")
            f.write(f"[CMD] {cmd}\n")
            f.write(f"[CWD] {cwd}\n")
            f.write("=" * 60 + "\n")
            f.flush()

            proc = subprocess.Popen(
                cmd,
                shell=True,
                cwd=cwd,
                stdout=f,
                stderr=subprocess.STDOUT,
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

            with bg_jobs_lock:
                bg_jobs[job_id]["pid"] = proc.pid
                bg_jobs[job_id]["status"] = "running"

            returncode = proc.wait()

            f.write("\n" + "=" * 60 + "\n")
            f.write(f"[END] {datetime.now().isoformat()}\n")
            f.write(f"[RETURNCODE] {returncode}\n")

        with bg_jobs_lock:
            bg_jobs[job_id]["status"] = "done" if returncode == 0 else f"error:{returncode}"
            bg_jobs[job_id]["end_time"] = datetime.now().isoformat()

        logger.info(f"[BG_JOB] {job_id} 完了 returncode={returncode}")

    except Exception as e:
        with bg_jobs_lock:
            bg_jobs[job_id]["status"] = f"exception:{str(e)}"
        logger.error(f"[BG_JOB] {job_id} 例外: {e}")
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"\n[EXCEPTION] {e}\n")
        except Exception:
            pass


class ThreadingHTTPServer(ThreadingMixIn, http.server.HTTPServer):
    """各リクエストを別スレッドで処理するHTTPサーバー。
    長時間コマンド実行中も他のリクエストを受け付け続ける。"""
    daemon_threads = True


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

        # /log?job_id=xxx でバックグラウンドジョブのログ末尾を取得
        elif self.path.startswith("/log"):
            if not self.check_auth():
                self.send_json(401, {"error": "unauthorized"})
                return
            from urllib.parse import urlparse, parse_qs
            qs = parse_qs(urlparse(self.path).query)
            job_id = qs.get("job_id", [None])[0]
            lines = int(qs.get("lines", [30])[0])

            if not job_id:
                # job_idなしなら全ジョブ一覧
                with bg_jobs_lock:
                    self.send_json(200, {"jobs": dict(bg_jobs)})
                return

            with bg_jobs_lock:
                job = bg_jobs.get(job_id)

            if not job:
                self.send_json(404, {"error": f"job not found: {job_id}"})
                return

            log_file = job.get("log_file", "")
            try:
                with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                    all_lines = f.readlines()
                tail = "".join(all_lines[-lines:])
            except Exception as e:
                tail = f"(ログ読み込みエラー: {e})"

            self.send_json(200, {
                "job_id": job_id,
                "status": job.get("status"),
                "pid": job.get("pid"),
                "start_time": job.get("start_time"),
                "end_time": job.get("end_time"),
                "log_tail": tail,
                "log_file": log_file,
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

        # ========== /run : コマンド実行（同期） ==========
        if path == "/run":
            cmd = req.get("cmd", "")
            cwd = req.get("cwd", r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
            timeout = min(int(req.get("timeout", 60)), MAX_TIMEOUT)

            if not cmd:
                self.send_json(400, {"error": "cmd is required"})
                return

            logger.info(f"[RUN] cmd={cmd} cwd={cwd} timeout={timeout}s")
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

        # ========== /run_bg : バックグラウンド非同期実行 ==========
        elif path == "/run_bg":
            cmd = req.get("cmd", "")
            cwd = req.get("cwd", r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
            job_id = req.get("job_id", datetime.now().strftime("%Y%m%d_%H%M%S"))

            if not cmd:
                self.send_json(400, {"error": "cmd is required"})
                return

            log_file = os.path.join(BG_LOG_DIR, f"{job_id}.log")

            with bg_jobs_lock:
                bg_jobs[job_id] = {
                    "status": "starting",
                    "cmd": cmd,
                    "cwd": cwd,
                    "log_file": log_file,
                    "start_time": datetime.now().isoformat(),
                    "pid": None,
                    "end_time": None,
                }

            t = threading.Thread(
                target=run_bg_job,
                args=(job_id, cmd, cwd, log_file),
                daemon=True,
            )
            t.start()

            logger.info(f"[RUN_BG] job_id={job_id} cmd={cmd}")
            self.send_json(200, {
                "job_id": job_id,
                "status": "started",
                "log_file": log_file,
                "message": f"GET /log?job_id={job_id} でログ確認"
            })

        # ========== /write_and_run : ファイル書き込み → 実行 ==========
        elif path == "/write_and_run":
            filepath = req.get("filepath", "")
            content = req.get("content", "")
            run_cmd = req.get("run_cmd", "")
            cwd = req.get("cwd", r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
            timeout = min(int(req.get("timeout", 120)), MAX_TIMEOUT)

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
                    logger.info(f"[RUN after write] {run_cmd} timeout={timeout}s")
                    result = subprocess.run(
                        run_cmd, shell=True, cwd=cwd,
                        capture_output=True, text=True,
                        encoding="utf-8", errors="replace", timeout=timeout,
                    )
                    result_data.update({
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "returncode": result.returncode,
                    })

                self.send_json(200, result_data)
            except subprocess.TimeoutExpired:
                self.send_json(408, {"error": f"timeout after {timeout}s", "cmd": run_cmd})
            except Exception as e:
                self.send_json(500, {"error": str(e)})

        else:
            self.send_json(404, {"error": f"unknown endpoint: {path}"})


def run():
    logger.info(f"ジョブズ コマンドサーバー v3 起動 → localhost:{PORT}")
    logger.info(f"ThreadingHTTPServer: 有効（並列リクエスト対応）")
    logger.info(f"最大timeout: {MAX_TIMEOUT}秒")
    logger.info(f"BGログディレクトリ: {BG_LOG_DIR}")
    server = ThreadingHTTPServer(("127.0.0.1", PORT), CommandHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("サーバー停止")
        server.shutdown()


if __name__ == "__main__":
    run()
