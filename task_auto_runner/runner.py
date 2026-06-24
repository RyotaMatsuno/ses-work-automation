"""task_auto_runner メインループ。pending_tasks/ を消化する。"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# パス設定
SES_WORK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SES_WORK))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from claude_invoker import invoke_claude_code
from gate_runner import (
    extract_target_file,
    handle_ng,
    move_to_done,
    run_gate_check,
)
from notifier import (
    notify_blocked,
    notify_cost_guard,
    notify_retry,
    notify_success,
    notify_timeout,
)

PENDING = SES_WORK / "pending_tasks"
RUNNING = SES_WORK / "running_tasks"
LOGS = Path(__file__).resolve().parent / "logs"
LOCK_FILE = LOGS / "runner.lock"

MONTHLY_LIMIT_USD = 140.0
DAILY_RUNNER_BUDGET_USD = 15.0  # Claude Code実行の日次上限（runner独自）
MAX_TASKS_PER_RUN = 3  # 1起動あたりの最大タスク数（暴走防止）


def setup_logger() -> logging.Logger:
    LOGS.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y%m%d")
    log_path = LOGS / f"runner_{today}.log"
    logger = logging.getLogger("task_auto_runner")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(fh)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(sh)
    return logger


def check_pid_alive(pid: int) -> bool:
    """Windowsで指定PIDが生きているか確認。"""
    try:
        import subprocess

        result = subprocess.run(
            ["tasklist", "/fi", f"PID eq {pid}", "/fo", "csv", "/nh"], capture_output=True, text=True, timeout=10
        )
        return str(pid) in result.stdout
    except Exception:
        return False


def acquire_lock(logger) -> bool:
    LOGS.mkdir(parents=True, exist_ok=True)
    if LOCK_FILE.exists():
        try:
            old_pid = int(LOCK_FILE.read_text().strip())
            if check_pid_alive(old_pid):
                logger.warning(f"既存プロセス稼働中 PID={old_pid} → exit")
                return False
            else:
                logger.info(f"古いlockを除去 PID={old_pid}")
                LOCK_FILE.unlink()
        except Exception:
            LOCK_FILE.unlink()
    LOCK_FILE.write_text(str(os.getpid()))
    return True


def release_lock():
    if LOCK_FILE.exists():
        try:
            LOCK_FILE.unlink()
        except Exception:
            pass


def check_cost_guard(logger) -> bool:
    """月次CostGuard確認。$140超ならFalse。"""
    try:
        sys.path.insert(0, str(SES_WORK))
        import cost_guard

        hourly, daily, monthly = cost_guard.get_costs()
        logger.info(f"CostGuard: monthly=${monthly:.2f} daily=${daily:.2f}")
        if monthly >= MONTHLY_LIMIT_USD:
            notify_cost_guard(monthly)
            return False
        return True
    except Exception as exc:
        logger.warning(f"CostGuard チェック失敗（続行）: {exc}")
        return True


def scan_pending_tasks() -> list[Path]:
    """pending_tasks/*.md を mtime 古い順で返す。"""
    if not PENDING.exists():
        return []
    files = [p for p in PENDING.glob("*.md") if p.is_file()]
    files.sort(key=lambda p: p.stat().st_mtime)
    return files


def process_one(task_path: Path, logger, dry_run: bool = False) -> dict:
    """1指示書を実行。戻り値: {action, cost, duration, reason}"""
    logger.info(f"=== 開始: {task_path.name} ===")
    RUNNING.mkdir(parents=True, exist_ok=True)
    running_log = RUNNING / f"{task_path.stem}.log"
    running_log.write_text(f"started: {datetime.now().isoformat()}\n", encoding="utf-8")

    if dry_run:
        logger.info(f"[dry-run] would execute: {task_path.name}")
        return {"action": "dry_run", "cost": 0.0, "duration": 0.0, "reason": ""}

    # 指示書を読む
    instruction_text = task_path.read_text(encoding="utf-8")

    # Claude Code 起動
    # 実行前: runner日次予算チェック（Claude Code分の独自管理）
    spent_today = _runner_cost_today()
    if spent_today >= DAILY_RUNNER_BUDGET_USD:
        logger.warning(f"runner日次予算超過 ${spent_today:.2f}/{DAILY_RUNNER_BUDGET_USD} → 実行スキップ")
        return {"action": "budget_skip", "cost": 0.0, "duration": 0.0, "reason": "daily budget exceeded"}

    res = invoke_claude_code(str(task_path), budget_usd=5.0, timeout=1500)

    # 実行後: コストをledger + runner独自ログの両方に記録
    if res.cost_usd > 0:
        _record_runner_cost(res.cost_usd, task_path.name)
        try:
            from common.ledger import record as ledger_record

            ledger_record(0, 0, "claude-code-cli", actual_usd=res.cost_usd)
        except TypeError:
            # ledger.recordのシグネチャ違いに対応
            try:
                from common.ledger import record as ledger_record

                ledger_record(int(res.cost_usd * 100000), 0, "claude-code-cli")
            except Exception:
                pass
        except Exception:
            pass
    with open(running_log, "a", encoding="utf-8") as f:
        f.write(f"claude_exit={res.exit_code} duration={res.duration_sec:.1f}s cost=${res.cost_usd:.4f}\n")
        if res.stderr:
            f.write(f"stderr:\n{res.stderr[:2000]}\n")
        f.write(f"stdout_tail:\n{res.stdout[-2000:]}\n")

    if res.timeout:
        logger.warning(f"Claude Code TIMEOUT: {task_path.name}")
        notify_timeout(task_path.name)
        action, new_path = handle_ng(task_path, "Claude Code TIMEOUT")
        if action == "retry":
            notify_retry(new_path.name, _parse_try(new_path.name), "TIMEOUT")
        else:
            notify_blocked(new_path.name, "Claude Code TIMEOUT x2")
        return {"action": action, "cost": 0.0, "duration": res.duration_sec, "reason": "TIMEOUT"}

    if res.exit_code != 0:
        logger.warning(f"Claude Code exit={res.exit_code}: {task_path.name}")
        reason = f"exit={res.exit_code} / stderr={res.stderr[:300]}"
        action, new_path = handle_ng(task_path, reason)
        if action == "retry":
            notify_retry(new_path.name, _parse_try(new_path.name), reason)
        else:
            notify_blocked(new_path.name, reason)
        return {"action": action, "cost": res.cost_usd, "duration": res.duration_sec, "reason": reason}

    # 成功 → ゲート②
    target = extract_target_file(instruction_text)
    logger.info(f"ゲート②対象: {target}")
    gate = run_gate_check(target, phase="implementation", timeout=120)
    logger.info(f"ゲート結果: judgment={gate.judgment} verdict={gate.verdict}")

    if gate.verdict == "OK":
        dest = move_to_done(task_path)
        notify_success(task_path.name, res.cost_usd, res.duration_sec)
        return {"action": "done", "cost": res.cost_usd, "duration": res.duration_sec, "reason": ""}
    else:
        action, new_path = handle_ng(task_path, gate.reason)
        if action == "retry":
            notify_retry(new_path.name, _parse_try(new_path.name), gate.reason)
        else:
            notify_blocked(new_path.name, gate.reason)
        return {"action": action, "cost": res.cost_usd, "duration": res.duration_sec, "reason": gate.reason}


def _runner_cost_today() -> float:
    """runner独自のClaude Code日次コスト集計。"""
    cost_file = LOGS / "runner_cost.jsonl"
    if not cost_file.exists():
        return 0.0
    today = datetime.now().strftime("%Y-%m-%d")
    total = 0.0
    try:
        for line in cost_file.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
                if r.get("date") == today:
                    total += float(r.get("cost_usd", 0))
            except Exception:
                continue
    except Exception:
        pass
    return total


def _record_runner_cost(cost_usd: float, task_name: str) -> None:
    """Claude Code実行コストをrunner独自ログに記録。"""
    cost_file = LOGS / "runner_cost.jsonl"
    entry = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "ts": datetime.now().isoformat(),
        "cost_usd": cost_usd,
        "task": task_name,
    }
    try:
        with open(cost_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _parse_try(filename: str) -> int:
    import re

    m = re.search(r"__try(\d+)\.md$", filename)
    return int(m.group(1)) if m else 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-tasks", type=int, default=MAX_TASKS_PER_RUN, help="1回の起動で処理する最大件数")
    args = parser.parse_args()

    logger = setup_logger()
    logger.info(f"=== task_auto_runner 起動 (dry_run={args.dry_run}) ===")

    if not acquire_lock(logger):
        sys.exit(0)

    try:
        if not check_cost_guard(logger):
            logger.error("CostGuard発動 → abort")
            sys.exit(0)

        tasks = scan_pending_tasks()
        logger.info(f"pending_tasks 件数: {len(tasks)}")
        if not tasks:
            logger.info("No pending tasks")
            return

        processed = 0
        for task in tasks[: args.max_tasks]:
            try:
                result = process_one(task, logger, dry_run=args.dry_run)
                logger.info(f"--- 結果: {task.name} action={result['action']} cost=${result['cost']:.4f}")
                processed += 1
            except Exception as exc:
                logger.exception(f"処理中エラー {task.name}: {exc}")

        logger.info(f"処理完了: {processed}/{len(tasks)} 件")
    finally:
        release_lock()


if __name__ == "__main__":
    main()
