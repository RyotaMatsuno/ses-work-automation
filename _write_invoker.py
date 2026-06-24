# claude_invoker.py - Claude Code CLI ラッパ
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

content = '''"""Claude Code CLI ラッパ。指示書を渡して実装させる。"""
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

CLAUDE_CMD = r"C:\\Users\\ma_py\\AppData\\Roaming\\npm\\claude.cmd"
DEFAULT_TIMEOUT = 1500
DEFAULT_BUDGET_USD = 5.0


@dataclass
class InvokeResult:
    exit_code: int
    stdout: str
    stderr: str
    duration_sec: float
    cost_usd: float
    timeout: bool = False
    raw_json: dict = None


def invoke_claude_code(
    instruction_path: str,
    budget_usd: float = DEFAULT_BUDGET_USD,
    timeout: int = DEFAULT_TIMEOUT,
    add_dir: str = None,
    model: str = "sonnet",
) -> InvokeResult:
    """指示書ファイルを Claude Code に渡して実装させる。"""
    if not os.path.exists(instruction_path):
        return InvokeResult(
            exit_code=-2,
            stdout="",
            stderr=f"instruction_path not found: {instruction_path}",
            duration_sec=0.0,
            cost_usd=0.0,
        )

    with open(instruction_path, encoding="utf-8") as f:
        instruction_text = f.read()

    ses_work = add_dir or os.getcwd()

    # システム指示を前置: ses_work外に書き込まない、完了したら明示マーカー
    system_prefix = (
        "あなたは Claude Code として実装を行います。\\n"
        "- ses_work ディレクトリ外への書き込みは禁止です。\\n"
        "- 実装完了時は最後に IMPL_COMPLETE という文字列を必ず出力してください。\\n"
        "- TASKS.md があれば各タスクのチェックボックスを更新してください。\\n\\n"
        "## 指示書本文\\n\\n"
    )
    full_prompt = system_prefix + instruction_text

    cmd = [
        CLAUDE_CMD,
        "-p", full_prompt,
        "--dangerously-skip-permissions",
        "--model", model,
        "--max-budget-usd", str(budget_usd),
        "--output-format", "json",
        "--no-session-persistence",
        "--add-dir", ses_work,
    ]

    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            cwd=ses_work,
            timeout=timeout,
            shell=False,
        )
        duration = time.time() - start
        stdout = result.stdout.decode("utf-8", errors="replace")
        stderr = result.stderr.decode("utf-8", errors="replace")
        cost = 0.0
        raw = None
        # JSON出力からコスト抽出
        try:
            # 最後のJSONブロックを抽出
            last_brace = stdout.rfind("{")
            if last_brace != -1:
                raw = json.loads(stdout[last_brace:])
                cost = float(raw.get("total_cost_usd", 0) or raw.get("cost_usd", 0) or 0)
        except Exception:
            pass
        return InvokeResult(
            exit_code=result.returncode,
            stdout=stdout,
            stderr=stderr,
            duration_sec=duration,
            cost_usd=cost,
            timeout=False,
            raw_json=raw,
        )
    except subprocess.TimeoutExpired as e:
        duration = time.time() - start
        return InvokeResult(
            exit_code=-1,
            stdout=(e.stdout or b"").decode("utf-8", errors="replace") if e.stdout else "",
            stderr=f"TIMEOUT after {timeout}s",
            duration_sec=duration,
            cost_usd=0.0,
            timeout=True,
        )
    except Exception as exc:
        return InvokeResult(
            exit_code=-3,
            stdout="",
            stderr=f"unexpected error: {exc}",
            duration_sec=time.time() - start,
            cost_usd=0.0,
        )


if __name__ == "__main__":
    # 単体テスト用: 引数で指示書パスを受ける
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("instruction_path")
    p.add_argument("--budget", type=float, default=DEFAULT_BUDGET_USD)
    p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    args = p.parse_args()

    res = invoke_claude_code(args.instruction_path, budget_usd=args.budget, timeout=args.timeout)
    print(f"exit={res.exit_code} duration={res.duration_sec:.1f}s cost=${res.cost_usd:.4f}")
    print(f"stdout tail: {res.stdout[-500:]}")
    if res.stderr:
        print(f"stderr: {res.stderr[-500:]}")
'''

with open("task_auto_runner/claude_invoker.py", "w", encoding="utf-8") as f:
    f.write(content)
print(f"claude_invoker.py: {os.path.getsize('task_auto_runner/claude_invoker.py')} bytes")
