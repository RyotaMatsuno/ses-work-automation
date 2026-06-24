import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from datetime import datetime

# バックアップ
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copy("task_auto_runner/runner.py", f"task_auto_runner/runner.py.bak_{ts}")

with open("task_auto_runner/runner.py", encoding="utf-8") as f:
    content = f.read()

# === 修正1: MONTHLY_LIMIT_USD の下に日次Claude Code予算を追加 ===
old1 = "MONTHLY_LIMIT_USD = 140.0"
new1 = """MONTHLY_LIMIT_USD = 140.0
DAILY_RUNNER_BUDGET_USD = 15.0  # Claude Code実行の日次上限（runner独自）
MAX_TASKS_PER_RUN = 3           # 1起動あたりの最大タスク数（暴走防止）"""
content = content.replace(old1, new1)

# === 修正2: max-tasksのデフォルトを3に ===
old2 = 'parser.add_argument("--max-tasks", type=int, default=10, help="1回の起動で処理する最大件数")'
new2 = 'parser.add_argument("--max-tasks", type=int, default=MAX_TASKS_PER_RUN, help="1回の起動で処理する最大件数")'
content = content.replace(old2, new2)

# === 修正3: process_one内でClaude Codeコストをledgerに記録 ===
old3 = """    res = invoke_claude_code(str(task_path), budget_usd=5.0, timeout=1500)"""
new3 = """    # 実行前: runner日次予算チェック（Claude Code分の独自管理）
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
            pass"""
content = content.replace(old3, new3)

# === 修正4: _runner_cost_today / _record_runner_cost 関数を追加 ===
old4 = "def _parse_try(filename: str) -> int:"
new4 = '''def _runner_cost_today() -> float:
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
            f.write(json.dumps(entry, ensure_ascii=False) + "\\n")
    except Exception:
        pass


def _parse_try(filename: str) -> int:'''
content = content.replace(old4, new4)

with open("task_auto_runner/runner.py", "w", encoding="utf-8") as f:
    f.write(content)

# 構文チェック
import subprocess

r = subprocess.run(["python", "-m", "py_compile", "task_auto_runner/runner.py"], capture_output=True, text=True)
print("構文:", "✅ OK" if r.returncode == 0 else f"❌ {r.stderr}")
