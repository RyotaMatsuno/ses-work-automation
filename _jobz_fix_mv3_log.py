import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES = os.getcwd()
mv3 = os.path.join(SES, "matching_v3", "matching_v3.py")

with open(mv3, encoding="utf-8") as f:
    content = f.read()

old = """def _setup_logging() -> None:
    log_dir = BASE_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            logging.FileHandler(log_dir / f"matching_v3_{datetime.now(JST):%Y%m%d}.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    for handler in logging.getLogger().handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
            handler.setLevel(logging.WARNING)"""

new = """def _setup_logging() -> None:
    log_dir = BASE_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    # force=True: flag_auto_updater が先にハンドラーを設定していても必ず上書きする
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            logging.FileHandler(log_dir / f"matching_v3_{datetime.now(JST):%Y%m%d}.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )
    for handler in logging.getLogger().handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
            handler.setLevel(logging.WARNING)"""

if old in content:
    new_content = content.replace(old, new)
    with open(mv3, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("matching_v3 _setup_logging 修正完了 (force=True追加)")
else:
    print("ERROR: 置換対象が見つかりません")
    # 現状の _setup_logging を表示
    for i, line in enumerate(content.split("\n"), 1):
        if "basicConfig" in line or "force" in line:
            print(f"  L{i}: {repr(line)}")
