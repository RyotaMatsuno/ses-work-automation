#!/usr/bin/env python3
"""自動ダブルチェックシステム - ゲート①/②をGPT-4oで実施。"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent
SES_WORK = BASE_DIR.parent
RESULTS_DIR = BASE_DIR / "results"
DAILY_COUNTER_PATH = RESULTS_DIR / "daily_counter.json"

DAILY_CALL_LIMIT = 10
REVIEW_MODEL = "gpt-4o"
MAX_RETRIES = 3
SCRIPT_NAME = "gate_checker"

JST = timezone(timedelta(hours=9))

REQUIREMENTS_SYSTEM = """あなたはSES業界のシステム設計レビュー専門AIです。
SPEC.mdを厳密にレビューし、以下の観点で問題を指摘してください。

1. ロジックの抜け/矛盾
2. エッジケース漏れ
3. CostGuardの被覆
4. 危険パラメータの無断増加リスク
5. テスト網羅性
6. 人間確認ゲートの明記
7. ロールバック可能性

各観点について具体的にコメントし、最後に必ず以下のいずれか1行で判定してください:
【判定: GO】
【判定: 条件付きGO】
【判定: NG】

GO = 問題なしで実装着手可
条件付きGO = 軽微な指摘ありだが実装着手可
NG = 重大な問題があり実装着手不可"""

IMPLEMENTATION_SYSTEM = """あなたはSES業界のコードレビュー専門AIです。
実装コードとSPEC.mdを照合し、以下の観点で問題を指摘してください。

1. CostGuard被覆漏れ
2. 自動送信・本番DB書き込みが人間確認なしで起きる経路
3. SPEC制約との整合性
4. 明らかなバグ（インポートエラー・未定義変数）
5. セキュリティ（認証・署名検証）

各観点について具体的にコメントし、最後に必ず以下のいずれか1行で判定してください:
【判定: GO】
【判定: NG】"""

logger = logging.getLogger(SCRIPT_NAME)


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _load_env() -> dict[str, str]:
    env_path = SES_WORK / "config" / ".env"
    env: dict[str, str] = {}
    if not env_path.exists():
        return env
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def resolve_path(file_arg: str) -> Path:
    """相対パスを cwd → gate_checker/ の順で解決。"""
    candidate = Path(file_arg)
    if candidate.is_absolute() and candidate.exists():
        return candidate.resolve()
    for base in (Path.cwd(), BASE_DIR, SES_WORK):
        resolved = (base / file_arg).resolve()
        if resolved.exists():
            return resolved
    raise FileNotFoundError(f"ファイルが見つかりません: {file_arg}")


def resolve_tasks_path(target_file: Path, tasks_arg: str | None) -> Path | None:
    if tasks_arg:
        return resolve_path(tasks_arg)
    tasks = target_file.parent / "TASKS.md"
    return tasks if tasks.exists() else None


def _today_str() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d")


def load_daily_counter() -> dict[str, Any]:
    if not DAILY_COUNTER_PATH.exists():
        return {"date": _today_str(), "count": 0}
    try:
        data = json.loads(DAILY_COUNTER_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"date": _today_str(), "count": 0}
    if data.get("date") != _today_str():
        return {"date": _today_str(), "count": 0}
    return {"date": _today_str(), "count": int(data.get("count", 0))}


def save_daily_counter(count: int) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"date": _today_str(), "count": count}
    DAILY_COUNTER_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def check_daily_limit() -> tuple[bool, int]:
    counter = load_daily_counter()
    count = int(counter["count"])
    return count < DAILY_CALL_LIMIT, count


def increment_daily_counter() -> int:
    counter = load_daily_counter()
    new_count = int(counter["count"]) + 1
    save_daily_counter(new_count)
    return new_count


def parse_judgment(review_text: str) -> tuple[str, str]:
    """レビュー本文から判定を抽出。戻り値: (judgment, verdict)"""
    patterns = [
        r"【判定[:：]\s*(GO|条件付きGO|NG)】",
        r"判定[:：]\s*(GO|条件付きGO|NG)",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, review_text, flags=re.IGNORECASE)
        if matches:
            raw = matches[-1].upper()
            if "条件付き" in matches[-1] or raw == "条件付きGO":
                return "条件付きGO", "OK"
            if raw == "GO":
                return "GO", "OK"
            if raw == "NG":
                return "NG", "NG"
    upper = review_text.upper()
    if "【判定: NG】" in review_text or "判定: NG" in upper:
        return "NG", "NG"
    if "条件付きGO" in review_text:
        return "条件付きGO", "OK"
    if "【判定: GO】" in review_text or re.search(r"判定[:：]\s*GO", review_text):
        return "GO", "OK"
    logger.warning("判定をパースできませんでした。NGとして扱います。")
    return "UNKNOWN", "NG"


def build_user_prompt(phase: str, target_file: Path) -> str:
    spec_text = target_file.read_text(encoding="utf-8")
    parts = [f"# レビュー対象: {target_file.name}\n\n{spec_text}"]

    claude_md = target_file.parent / "CLAUDE.md"
    if claude_md.exists():
        parts.append(f"\n\n# 参考: CLAUDE.md\n\n{claude_md.read_text(encoding='utf-8')}")

    if phase == "implementation":
        spec_md = target_file.parent / "SPEC.md"
        if spec_md.exists() and spec_md.resolve() != target_file.resolve():
            parts.append(f"\n\n# 参考: SPEC.md\n\n{spec_md.read_text(encoding='utf-8')}")

    return "\n".join(parts)


def call_gpt4o(system_prompt: str, user_prompt: str, api_key: str) -> tuple[str, int, int]:
    sys.path.insert(0, str(SES_WORK))
    try:
        from common.ledger import can_spend, record
    except ImportError:
        can_spend = None
        record = None

    est_in = max(500, len(user_prompt) // 3)
    est_out = 1500
    if can_spend is not None and not can_spend(est_in, est_out, REVIEW_MODEL):
        raise RuntimeError("CostGuard: コスト上限によりAPI呼び出しを拒否しました")

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("openai package is required: pip install openai") from exc

    client = OpenAI(api_key=api_key)
    last_error: Exception | None = None

    for attempt in range(MAX_RETRIES):
        try:
            resp = client.chat.completions.create(
                model=REVIEW_MODEL,
                max_tokens=3000,
                temperature=0,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            text = resp.choices[0].message.content or ""
            usage = resp.usage
            in_tokens = int(getattr(usage, "prompt_tokens", 0) or est_in)
            out_tokens = int(getattr(usage, "completion_tokens", 0) or est_out)
            if record is not None:
                record(in_tokens, out_tokens, REVIEW_MODEL, SCRIPT_NAME)
            return text, in_tokens, out_tokens
        except Exception as exc:
            last_error = exc
            err_str = str(exc)
            if "429" in err_str and attempt < MAX_RETRIES - 1:
                wait = 2 ** attempt
                logger.warning("Rate limit (429). %ds後にリトライ...", wait)
                time.sleep(wait)
                continue
            raise
    raise RuntimeError(f"API呼び出し失敗: {last_error}")


def update_tasks_on_ng(tasks_path: Path, phase: str) -> bool:
    """NG時にTASKS.mdのゲートフラグを [!] に更新。"""
    if not tasks_path.exists():
        logger.warning("TASKS.mdが見つかりません: %s", tasks_path)
        return False

    content = tasks_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    gate_keyword = "ゲート①" if phase == "requirements" else "ゲート②"
    today = datetime.now(JST).strftime("%Y-%m-%d")
    suffix = f"（{today} GPT-4o判定:NG）"
    updated = False
    new_lines: list[str] = []

    for line in lines:
        if not updated and gate_keyword in line and "- [ ]" in line:
            new_line = line.replace("- [ ]", "- [!]", 1)
            if suffix not in new_line:
                new_line = new_line.rstrip() + " " + suffix
            new_lines.append(new_line)
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        for i, line in enumerate(new_lines):
            if "- [ ]" in line:
                new_line = line.replace("- [ ]", "- [!]", 1)
                if suffix not in new_line:
                    new_line = new_line.rstrip() + " " + suffix
                new_lines[i] = new_line
                updated = True
                break

    if updated:
        tasks_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        logger.info("TASKS.mdを更新しました: %s", tasks_path)
    return updated


def save_result(payload: dict[str, Any]) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(JST).strftime("%Y%m%d_%H%M%S")
    out_path = RESULTS_DIR / f"gate_{payload['phase']}_{ts}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("結果を保存: %s", out_path)
    return out_path


def run_gate_check(phase: str, file_arg: str, tasks_arg: str | None) -> int:
    if phase not in ("requirements", "implementation"):
        logger.error("不正なphase: %s（requirements / implementation）", phase)
        return 1

    allowed, current_count = check_daily_limit()
    if not allowed:
        logger.error("日次上限超過: %d/%d 回使用済み", current_count, DAILY_CALL_LIMIT)
        payload = {
            "timestamp": datetime.now(JST).isoformat(),
            "phase": phase,
            "target_file": file_arg,
            "verdict": "LIMIT_EXCEEDED",
            "judgment": "LIMIT_EXCEEDED",
            "review_text": f"日次上限 {DAILY_CALL_LIMIT} 回に達しました（本日 {current_count} 回使用済み）",
            "model": REVIEW_MODEL,
            "input_tokens": 0,
            "output_tokens": 0,
            "daily_count": current_count,
        }
        save_result(payload)
        return 2

    try:
        target_file = resolve_path(file_arg)
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 1

    tasks_path = resolve_tasks_path(target_file, tasks_arg)
    env = _load_env()
    api_key = env.get("OPENAI_API_KEY", "")
    if not api_key:
        logger.error("OPENAI_API_KEYが設定されていません（config/.env）")
        return 1

    system_prompt = REQUIREMENTS_SYSTEM if phase == "requirements" else IMPLEMENTATION_SYSTEM
    user_prompt = build_user_prompt(phase, target_file)

    logger.info("ゲートチェック開始: phase=%s file=%s", phase, target_file)

    try:
        review_text, in_tokens, out_tokens = call_gpt4o(system_prompt, user_prompt, api_key)
    except Exception as exc:
        logger.error("API呼び出しエラー: %s", exc)
        payload = {
            "timestamp": datetime.now(JST).isoformat(),
            "phase": phase,
            "target_file": str(target_file),
            "tasks_file": str(tasks_path) if tasks_path else None,
            "verdict": "ERROR",
            "judgment": "ERROR",
            "review_text": str(exc),
            "model": REVIEW_MODEL,
            "input_tokens": 0,
            "output_tokens": 0,
            "daily_count": current_count,
        }
        save_result(payload)
        return 1

    daily_count = increment_daily_counter()
    judgment, verdict = parse_judgment(review_text)

    payload = {
        "timestamp": datetime.now(JST).isoformat(),
        "phase": phase,
        "target_file": str(target_file),
        "tasks_file": str(tasks_path) if tasks_path else None,
        "verdict": verdict,
        "judgment": judgment,
        "review_text": review_text,
        "model": REVIEW_MODEL,
        "input_tokens": in_tokens,
        "output_tokens": out_tokens,
        "daily_count": daily_count,
    }
    result_path = save_result(payload)

    print(f"\n{'='*60}")
    print(review_text)
    print(f"{'='*60}")
    print(f"判定: {judgment} → verdict={verdict}")
    print(f"結果JSON: {result_path}")
    print(f"本日の使用回数: {daily_count}/{DAILY_CALL_LIMIT}")

    if verdict == "NG":
        if tasks_path:
            update_tasks_on_ng(tasks_path, phase)
        return 1
    return 0


def main() -> None:
    _setup_logging()
    parser = argparse.ArgumentParser(description="自動ダブルチェックシステム（gate_checker）")
    parser.add_argument("--phase", required=True, choices=["requirements", "implementation"])
    parser.add_argument("--file", required=True, help="レビュー対象ファイル")
    parser.add_argument("--tasks", default=None, help="TASKS.mdパス（省略時は対象と同ディレクトリ）")
    args = parser.parse_args()
    sys.exit(run_gate_check(args.phase, args.file, args.tasks))


if __name__ == "__main__":
    main()
