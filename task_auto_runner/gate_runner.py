"""ゲート② 自動実行 + NG時の再投入ロジック。"""

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SES_WORK = Path(__file__).resolve().parent.parent
GATE_CHECK = SES_WORK / "gate_checker" / "gate_check.py"
PENDING = SES_WORK / "pending_tasks"
DONE = SES_WORK / "done_tasks"
BLOCKED = SES_WORK / "blocked_tasks"

MAX_TRY = 2  # 試行2回でblocked

TRY_PATTERN = re.compile(r"__try(\d+)\.md$")


@dataclass
class GateResult:
    verdict: str  # "OK" / "NG"
    judgment: str  # "GO" / "条件付きGO" / "NG"
    reason: str
    raw_output: str


def parse_try_number(filename: str) -> int:
    """ファイル名から試行回数を抽出。__tryN がなければ 0。"""
    m = TRY_PATTERN.search(filename)
    return int(m.group(1)) if m else 0


def strip_try(filename: str) -> str:
    """ファイル名から __tryN を除去。"""
    return TRY_PATTERN.sub(".md", filename)


def make_try_filename(original_filename: str, try_num: int) -> str:
    """__try{N}.md を付けたファイル名を返す。"""
    base = strip_try(original_filename)
    return base.replace(".md", f"__try{try_num}.md")


def extract_target_file(instruction_text: str) -> str:
    """指示書から対象ファイルを推定。"""
    # 「対象ファイル:」
    m = re.search(r"対象ファイル[:：]\s*([^\s\n]+)", instruction_text)
    if m:
        p = m.group(1).strip().rstrip("、,。")
        if (SES_WORK / p).exists():
            return str(SES_WORK / p)
    # 「対象ディレクトリ:」→ その下の SPEC.md があれば
    m = re.search(r"対象ディレクトリ[:：]\s*([^\s\n]+)", instruction_text)
    if m:
        d = m.group(1).strip().rstrip("/、,。").rstrip("\\")
        spec_path = SES_WORK / d / "SPEC.md"
        if spec_path.exists():
            return str(spec_path)
        # SPEC.md なければそのディレクトリ自体
        dir_path = SES_WORK / d
        if dir_path.exists():
            # 最新の .py を返す
            py_files = list(dir_path.rglob("*.py"))
            if py_files:
                latest = max(py_files, key=lambda x: x.stat().st_mtime)
                return str(latest)
    return ""


def run_gate_check(target_file: str, phase: str = "implementation", timeout: int = 120) -> GateResult:
    """gate_check.py を呼び出して結果を返す。
    target_file が未指定（空文字）の場合はゲートをスキップしてOKを返す。
    """
    if not target_file:
        return GateResult(
            verdict="OK",
            judgment="SKIP",
            reason="target_file未指定のためゲート②スキップ",
            raw_output="",
        )
    if not os.path.exists(target_file):
        return GateResult(
            verdict="NG",
            judgment="NG",
            reason=f"target_file not found: {target_file}",
            raw_output="",
        )
    cmd = [
        sys.executable,
        str(GATE_CHECK),
        "--phase",
        phase,
        "--file",
        target_file,
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            cwd=str(SES_WORK),
            timeout=timeout,
        )
        stdout = result.stdout.decode("utf-8", errors="replace")
        stderr = result.stderr.decode("utf-8", errors="replace")
        full = stdout + "\n" + stderr

        # 「合意判定: {GO|条件付きGO|NG}」を抽出
        m = re.search(r"合意判定[:：]\s*(GO|条件付きGO|NG)", full)
        if m:
            judgment = m.group(1)
            verdict = "OK" if judgment in ("GO", "条件付きGO") else "NG"
        else:
            # フォールバック: 【判定: X】
            m2 = re.search(r"【判定[:：]\s*(GO|条件付きGO|NG)】", full)
            if m2:
                judgment = m2.group(1)
                verdict = "OK" if judgment in ("GO", "条件付きGO") else "NG"
            else:
                judgment = "UNKNOWN"
                verdict = "NG" if result.returncode != 0 else "OK"

        # NG理由抽出: 「NG理由:」あるいはGPT出力末尾
        reason_match = re.search(r"NG理由[:：]\s*(.+?)(?:\n|$)", full)
        reason = reason_match.group(1) if reason_match else stdout[-500:]

        return GateResult(
            verdict=verdict,
            judgment=judgment,
            reason=reason,
            raw_output=full[-2000:],
        )
    except subprocess.TimeoutExpired:
        return GateResult(
            verdict="NG",
            judgment="TIMEOUT",
            reason=f"gate_check timeout after {timeout}s",
            raw_output="",
        )
    except Exception as exc:
        return GateResult(
            verdict="NG",
            judgment="ERROR",
            reason=str(exc),
            raw_output="",
        )


def move_to_done(src_path: Path) -> Path:
    """ファイルを done_tasks/ に移動。"""
    DONE.mkdir(parents=True, exist_ok=True)
    dest = DONE / src_path.name
    shutil.move(str(src_path), str(dest))
    return dest


def move_to_blocked(src_path: Path, reason: str = "") -> Path:
    """ファイルを blocked_tasks/ に移動。理由を末尾追記。"""
    BLOCKED.mkdir(parents=True, exist_ok=True)
    dest = BLOCKED / src_path.name
    if reason:
        with open(src_path, "a", encoding="utf-8") as f:
            f.write(f"\n\n## BLOCKED REASON\n{reason}\n")
    shutil.move(str(src_path), str(dest))
    return dest


def handle_ng(src_path: Path, reason: str) -> tuple[str, Path]:
    """NG時の処理。再投入 or blocked。
    戻り値: (action, new_path) action="retry" or "blocked"
    """
    cur_try = parse_try_number(src_path.name)
    next_try = cur_try + 1

    if next_try > MAX_TRY:
        dest = move_to_blocked(src_path, reason)
        return ("blocked", dest)

    # 再投入: pending_tasks/ に __try{N+1} で保存
    new_name = make_try_filename(src_path.name, next_try)
    new_path = PENDING / new_name
    with open(src_path, encoding="utf-8") as f:
        content = f.read()
    content += f"\n\n## RETRY {next_try} REASON\n{reason}\n"
    new_path.write_text(content, encoding="utf-8")
    # 元ファイルは削除
    src_path.unlink()
    return ("retry", new_path)
