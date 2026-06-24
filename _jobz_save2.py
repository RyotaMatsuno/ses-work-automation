import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

task = """【Cursor作業指示】
対象ファイル: ses_work/flag_auto_updater/run_flag_updater.py
作業内容: _setup_logging() の force=True によるログ乗っ取り修正

■ 問題
run_flag_updater.py の _setup_logging() が basicConfig(force=True) を使っている。
matching_v3.py から run_flag_updater() を呼び出すと、
matching_v3 が設定したルートロガー（matching_v3_YYYYMMDD.log 向け）を
flag_updater_YYYYMMDD.log に強制上書きしてしまう。
結果: matching_v3のINFO/ERRORログが全て flag_updater のlogファイルに流れ、
      matching_v3_YYYYMMDD.log は永久に空のまま。

■ 修正内容

【修正対象】flag_auto_updater/run_flag_updater.py の _setup_logging() 関数

【変更方針】
run_flag_updater() がサブルーチンとして呼ばれる場合（ルートロガーが既に設定済み）は
ファイルハンドラーを追加するだけにとどめ、force=True で上書きしない。

【具体的な修正】

変更前:
def _setup_logging() -> None:
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
    )

変更後:
def _setup_logging() -> None:
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
    )

■ 確認事項
1. matching_v3/matching_v3.py を実行後に matching_v3_YYYYMMDD.log にINFOログが出ること
2. flag_auto_updater/logs/flag_updater_YYYYMMDD.log にも同時に出ること
3. flag_auto_updater を単独実行した場合も flag_updater log に正常に出ること

■ 完了条件
- matching_v3.py 実行後に matching_v3_YYYYMMDD.log が空でなくなること

質問がある場合: Claude.aiチャットに貼り付けて確認
"""

import os
from pathlib import Path

SES = Path(os.getcwd())
pending_dir = SES / "local_server" / "pending_tasks"
pending_dir.mkdir(parents=True, exist_ok=True)

task_file = pending_dir / "fix_flag_updater_logging.md"
task_file.write_text(task, encoding="utf-8")
sz = task_file.stat().st_size
print(f"save OK: {task_file.name} ({sz}b)")
