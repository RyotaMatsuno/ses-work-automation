import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES = os.getcwd()
rfu = os.path.join(SES, "flag_auto_updater", "run_flag_updater.py")

with open(rfu, encoding="utf-8") as f:
    content = f.read()

old = """def _setup_logging() -> None:
    log_dir = BASE_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"flag_updater_{datetime.now(JST):%Y%m%d}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )"""

new = """def _setup_logging() -> None:
    log_dir = BASE_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"flag_updater_{datetime.now(JST):%Y%m%d}.log"

    root_logger = logging.getLogger()

    # 既にハンドラーが設定済み（親プロセスのlogging設定が生きている）場合は
    # flag_updater 専用のファイルハンドラーだけ追加する（force上書きしない）
    if root_logger.handlers:
        existing_paths = [
            getattr(h, "baseFilename", None)
            for h in root_logger.handlers
            if isinstance(h, logging.FileHandler)
        ]
        if str(log_path) not in existing_paths:
            flag_handler = logging.FileHandler(log_path, encoding="utf-8")
            flag_handler.setLevel(logging.INFO)
            flag_handler.setFormatter(
                logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
            )
            root_logger.addHandler(flag_handler)
        return

    # 単独起動時（ハンドラーなし）は従来通り basicConfig で設定
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )"""

if old in content:
    new_content = content.replace(old, new)
    with open(rfu, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("修正完了")
else:
    print("ERROR: 置換対象が見つかりません")
    # 差分確認
    print("現在の _setup_logging 内容:")
    for line in content.split("\n"):
        if "setup_logging" in line or "basicConfig" in line or "force" in line:
            print(f"  {repr(line)}")
