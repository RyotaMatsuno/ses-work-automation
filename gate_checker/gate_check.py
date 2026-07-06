#!/usr/bin/env python3
"""自動ダブルチェックシステム - 6フェーズ対応ゲートチェック。"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# agreement_checker (GPT+Sonnet並列)
try:
    from gate_checker.agreement_checker import AgreementDecision, is_ledger_blocked, run_dual_review
except ImportError:
    from agreement_checker import AgreementDecision, is_ledger_blocked, run_dual_review

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent
SES_WORK = BASE_DIR.parent
sys.path.insert(0, str(SES_WORK))
from cost_guard import allowed as _cg_allowed
from cost_guard import finalize as _cg_finalize

try:
    from common import ledger as _ledger
    _LEDGER_AVAILABLE = True
except ImportError:
    _ledger = None  # type: ignore[assignment]
    _LEDGER_AVAILABLE = False

RESULTS_DIR = BASE_DIR / "results"
PROMPTS_DIR = BASE_DIR / "prompts"
DAILY_COUNTER_PATH = RESULTS_DIR / "daily_counter.json"

DAILY_CALL_LIMIT = int(os.environ.get("GATE_DAILY_CALL_LIMIT") or 30)
REVIEW_MODEL = "gpt-4o"
SONNET_MODEL = "claude-sonnet-4-6"
MAX_RETRIES = 3
SCRIPT_NAME = "gate_check.py"  # ledger.record / _cg_allowed 共通（SPEC §11）

PHASES = ("research", "requirements", "design", "pre_impl", "implementation", "test")

JST = timezone(timedelta(hours=9))

COSTGUARD_NOTE = """
## 重要な注意事項
- CostGuardはLLM API呼び出し（OpenAI/Anthropic/Gemini）専用です
- Notion API、freee API、LINE Messaging API等の非LLM外部APIはCostGuard対象外です
- Notion DBへの読み書きは「自動送信」には該当しません（DB操作は確認不要）
- 承認済みの仕様変更（soft-skill all-pass、語彙外REVIEW化等）はNG判定しない
"""

REQUIREMENTS_SYSTEM = """あなたはSES業界のシステム設計レビュー専門AIです。
SPEC.mdを厳密にレビューし、以下の観点で問題を指摘してください。

1. ロジックの抜け/矛盾
2. エッジケース漏れ
3. CostGuardの被覆
4. 危険パラメータの無断増加リスク
5. テスト網羅性
6. 人間確認ゲートの明記
7. ロールバック可能性

**回答の1行目に必ず以下のいずれか1行で判定を書き、続けて各観点について具体的にコメントしてください:**
【判定: GO】
【判定: 条件付きGO】
【判定: NG】

GO = 問題なしで実装着手可
条件付きGO = 軽微な指摘ありだが実装着手可
NG = 重大な問題があり実装着手不可""" + COSTGUARD_NOTE

DESIGN_SYSTEM = """あなたはSES業界のシステム設計レビュー専門AIです。
SPEC.mdとTASKS.mdを照合し、以下の観点で問題を指摘してください。

1. SPECとTASKSの整合性
2. タスク分解の抜け・重複
3. 依存関係・実装順序の妥当性
4. CostGuard被覆と人間確認ゲートの明記
5. テスト方針の具体性

**回答の1行目に必ず以下のいずれか1行で判定を書き、続けて各観点について具体的にコメントしてください:**
【判定: GO】
【判定: 条件付きGO】
【判定: NG】""" + COSTGUARD_NOTE

IMPLEMENTATION_SYSTEM = """あなたはSES業界のコードレビュー専門AIです。
実装コードとSPEC.mdを照合し、以下の観点で問題を指摘してください。

1. CostGuard被覆漏れ
2. 自動送信・本番DB書き込みが人間確認なしで起きる経路
3. SPEC制約との整合性
4. 明らかなバグ（インポートエラー・未定義変数）
5. セキュリティ（認証・署名検証）

**回答の1行目に必ず以下のいずれか1行で判定を書き、続けて各観点について具体的にコメントしてください:**
【判定: GO】
【判定: NG】""" + COSTGUARD_NOTE

TEST_SYSTEM = """あなたはSES業界のテストレビュー専門AIです。
テスト結果（JSONまたはログ）を確認し、以下の観点で問題を指摘してください。

1. 失敗テスト・エラーの有無
2. 重要機能のカバレッジ不足
3. 再現性・環境依存の問題
4. デプロイ前に解消すべき重大リスク

**回答の1行目に必ず以下のいずれか1行で判定を書き、続けて各観点について具体的にコメントしてください:**
【判定: GO】
【判定: 条件付きGO】
【判定: NG】""" + COSTGUARD_NOTE

NOTIFY_TEMPLATE_NG = "[gate] {phase} NG: {filename} → ジョブズ対応中・返信不要"

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


def load_phase_prompt(phase: str) -> str:
    """prompts/{phase}.txt があれば読み込み、なければ組み込みプロンプトを返す。"""
    prompt_path = PROMPTS_DIR / f"{phase}.txt"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    builtin = {
        "requirements": REQUIREMENTS_SYSTEM,
        "design": DESIGN_SYSTEM,
        "implementation": IMPLEMENTATION_SYSTEM,
        "test": TEST_SYSTEM,
    }
    if phase in builtin:
        return builtin[phase]
    raise ValueError(f"プロンプト未定義: {phase}")


def needs_human_review(_phase: str, gpt_response: str) -> bool:
    """
    3層チェックで松野確認が必要かを判定。
    1層でもTrueになったら即座にTrueを返す。
    """

    EXACT_KEYWORDS = [
        "運用フロー",
        "仕様変更",
        "データ削除",
        "本番DB",
        "契約",
        "契約変更",
        "岡本",
        "コスト増",
        "費用が発生",
        "仕様修正",
        "要件変更",
    ]
    for kw in EXACT_KEYWORDS:
        if kw in gpt_response:
            return True

    SYNONYMS = {
        "運用フロー": [
            "オペレーション",
            "業務フロー",
            "作業手順",
            "フロー変更",
            "手順変更",
            "運用変更",
            "業務変更",
        ],
        "仕様変更": [
            "仕様修正",
            "要件変更",
            "動作変更",
            "挙動変更",
            "機能変更",
            "仕様追加",
            "仕様削除",
            "インターフェース変更",
        ],
        "データ削除": [
            "DB更新",
            "レコード削除",
            "データ消去",
            "初期化",
            "truncate",
            "drop",
            "データ移行",
            "スキーマ変更",
        ],
        "本番DB": [
            "本番環境",
            "プロダクション",
            "production",
            "本番データ",
            "本番サーバー",
            "本番反映",
        ],
        "契約": [
            "取引先",
            "クライアント",
            "単価",
            "契約先",
            "TERRA",
            "フラップ",
            "グレイスライン",
            "請求",
        ],
        "岡本": [
            "パートナー",
            "共同",
            "担当変更",
        ],
        "コスト増": [
            "料金増加",
            "費用増",
            "月額増",
            "追加費用",
            "課金",
            "API料金",
            "従量課金",
        ],
        "費用が発生": [
            "追加費用が発生",
            "課金が発生",
        ],
    }
    response_lower = gpt_response.lower()
    for synonyms in SYNONYMS.values():
        for synonym in synonyms:
            if synonym.lower() in response_lower:
                return True

    upper = gpt_response.upper()
    if "HUMAN_REVIEW: YES" in upper:
        return True
    if "HUMAN_REVIEW:" not in upper:
        return True

    return False


def resolve_human_review(verdict: str, phase: str, review_text: str) -> bool:
    human_review = needs_human_review(phase, review_text)
    # GOかつGPT自己判定NOの場合は誤検知を抑制（層3を最優先）
    if verdict == "OK" and "HUMAN_REVIEW: NO" in review_text.upper():
        human_review = False
    return human_review


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


def resolve_dir(dir_arg: str) -> Path:
    """ディレクトリパスを解決。"""
    candidate = Path(dir_arg)
    if candidate.is_absolute() and candidate.is_dir():
        return candidate.resolve()
    for base in (Path.cwd(), BASE_DIR, SES_WORK):
        resolved = (base / dir_arg).resolve()
        if resolved.is_dir():
            return resolved
    raise FileNotFoundError(f"ディレクトリが見つかりません: {dir_arg}")


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
    # research / pre_impl プロンプト形式（"GO" / "条件付きGO" / "NG"）
    for chunk in (review_text.strip()[:200], review_text.strip()[-200:]):
        if re.search(r'["\u201c]?(条件付きGO)["\u201d]?', chunk):
            return "条件付きGO", "OK"
        if re.search(r'["\u201c]?(NG)["\u201d]?', chunk):
            return "NG", "NG"
        if re.search(r'["\u201c]?(GO)["\u201d]?(?:\s|$|[。）)])', chunk) and "条件付き" not in chunk:
            return "GO", "OK"
    logger.warning("判定をパースできませんでした。NGとして扱います。")
    return "UNKNOWN", "NG"


def collect_source_files(dir_path: Path) -> str:
    parts: list[str] = []
    for py_file in sorted(dir_path.rglob("*.py")):
        if "__pycache__" in py_file.parts:
            continue
        rel = py_file.relative_to(dir_path)
        parts.append(f"## {rel}\n\n{py_file.read_text(encoding='utf-8')}")
    if not parts:
        raise ValueError(f"Pythonファイルが見つかりません: {dir_path}")
    return "\n\n".join(parts)


def build_user_prompt(phase: str, target_file: Path | None, dir_path: Path | None) -> str:
    if phase == "implementation" and dir_path is not None:
        parts = [f"# レビュー対象ディレクトリ: {dir_path}\n\n{collect_source_files(dir_path)}"]
        spec_md = dir_path.parent / "SPEC.md"
        if not spec_md.exists():
            spec_md = dir_path / "SPEC.md"
        if spec_md.exists():
            parts.append(f"\n\n# 参考: SPEC.md\n\n{spec_md.read_text(encoding='utf-8')}")
        claude_md = dir_path.parent / "CLAUDE.md"
        if claude_md.exists():
            parts.append(f"\n\n# 参考: CLAUDE.md\n\n{claude_md.read_text(encoding='utf-8')}")
        return "\n".join(parts)

    if target_file is None:
        raise ValueError("レビュー対象ファイルが指定されていません")

    spec_text = target_file.read_text(encoding="utf-8")
    parts = [f"# レビュー対象: {target_file.name}\n\n{spec_text}"]

    claude_md = target_file.parent / "CLAUDE.md"
    if claude_md.exists():
        parts.append(f"\n\n# 参考: CLAUDE.md\n\n{claude_md.read_text(encoding='utf-8')}")

    if phase == "design":
        spec_md = target_file.parent / "SPEC.md"
        if spec_md.exists() and spec_md.resolve() != target_file.resolve():
            parts.append(f"\n\n# 参考: SPEC.md\n\n{spec_md.read_text(encoding='utf-8')}")

    if phase == "implementation":
        spec_md = target_file.parent / "SPEC.md"
        if spec_md.exists() and spec_md.resolve() != target_file.resolve():
            parts.append(f"\n\n# 参考: SPEC.md\n\n{spec_md.read_text(encoding='utf-8')}")

    return "\n".join(parts)


def call_gpt4o(system_prompt: str, user_prompt: str, api_key: str) -> tuple[str, int, int]:
    # v1.0互換のため残存（run_gate_checkはrun_dual_reviewを使用。Week2で命名整理予定）
    est_in = max(500, len(user_prompt) // 3)
    est_out = 1500
    if _LEDGER_AVAILABLE:
        try:
            if not _ledger.can_spend(est_in, est_out, REVIEW_MODEL):
                raise RuntimeError("CostGuard(ledger): コスト上限によりAPI呼び出しを拒否しました")
        except RuntimeError:
            raise
        except Exception as exc:
            logger.warning("ledger.can_spend 呼び出し失敗（スキップ）: %s", exc)

    decision = _cg_allowed(
        phase="gate",
        block_type="gate_check",
        target_id=f"gate_{datetime.now(JST).strftime('%Y%m%d_%H%M%S')}",
        est_in=est_in,
        est_out=est_out,
        model_hint=REVIEW_MODEL,
        script=SCRIPT_NAME,
    )
    if not decision.allowed:
        raise RuntimeError(f"CostGuard: コスト上限によりAPI呼び出しを拒否しました (reason={decision.reason})")

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("openai package is required: pip install openai") from exc

    client = OpenAI(api_key=api_key)
    last_error: Exception | None = None
    error_kind = ""  # finalize の success 判定に使用
    in_tokens = 0
    out_tokens = 0
    response_text = ""

    try:
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
                response_text = resp.choices[0].message.content or ""
                usage = resp.usage
                in_tokens = int(getattr(usage, "prompt_tokens", 0) or est_in)
                out_tokens = int(getattr(usage, "completion_tokens", 0) or est_out)
                if _LEDGER_AVAILABLE:
                    try:
                        _ledger.record(in_tokens, out_tokens, REVIEW_MODEL, "gate_check.py", phase="gate")
                    except Exception as exc:
                        logger.warning("ledger.record 呼び出し失敗: %s", exc)
                return response_text, in_tokens, out_tokens
            except Exception as exc:
                last_error = exc
                err_str = str(exc)
                if "429" in err_str and attempt < MAX_RETRIES - 1:
                    wait = 2**attempt
                    logger.warning("Rate limit (429). %ds後にリトライ...", wait)
                    time.sleep(wait)
                    continue
                error_kind = "transient"
                raise
        error_kind = "transient"
        raise RuntimeError(f"API呼び出し失敗: {last_error}")
    finally:
        if decision.allowed:
            _cg_finalize(
                decision,
                in_tokens=in_tokens,
                out_tokens=out_tokens,
                success=(error_kind == ""),
                error_kind=error_kind,
            )


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
        if not updated and gate_keyword in line and "- [ ]" in line and "- [!]" not in line and "- [x]" not in line:
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


def _target_filename(target: str) -> str:
    if not target:
        return "(不明)"
    name = Path(target).name
    return name or target


def send_line_notification(
    phase: str,
    target: str,
    env: dict[str, str],
) -> bool:
    """NG判定時にLINEへ1行通知（返信不要・レビュー本文は送らない）。"""
    token = env.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    user_id = env.get("MATSUNO_USER_ID") or env.get("MATSUNO_LINE_USER_ID", "")
    if not token or not user_id:
        logger.warning("LINE通知スキップ: token=%s user_id=%s", bool(token), bool(user_id))
        return False

    filename = _target_filename(target)
    message = NOTIFY_TEMPLATE_NG.format(phase=phase, filename=filename)
    logger.info("LINE通知送信: %s", message)

    body = json.dumps(
        {"to": user_id, "messages": [{"type": "text", "text": message}]},
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        "https://api.line.me/v2/bot/message/push",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            logger.info("LINE通知送信完了: status=%s", response.status)
            return True
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        logger.error("LINE通知失敗: status=%s body=%s", exc.code, detail)
    except Exception as exc:
        logger.error("LINE通知失敗: %s", exc)
    return False


def run_wall_hitting(problem_text: str, phase: str, results_dir: Path) -> tuple[str, Path]:
    """技術的NGのときだけ壁打ちを自動実行。"""
    problem = problem_text.replace("\n", " ").strip()
    if len(problem) > 500:
        problem = problem[:500]

    result = subprocess.run(
        [sys.executable, "wall_hitting.py", "--problem", problem],
        capture_output=True,
        cwd=str(SES_WORK),
        timeout=60,
        encoding="utf-8",
        errors="replace",
    )
    output = result.stdout or result.stderr or ""
    ts = datetime.now(JST).strftime("%Y%m%d_%H%M%S")
    output_path = results_dir / f"wall_hitting_{phase}_{ts}.txt"
    results_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output, encoding="utf-8")
    logger.info("壁打ち結果を保存: %s", output_path)
    return output, output_path


def _target_label(file_arg: str | None, dir_arg: str | None) -> str:
    if dir_arg:
        return dir_arg
    return file_arg or ""


def run_gate_check(
    phase: str,
    file_arg: str | None,
    dir_arg: str | None,
    tasks_arg: str | None,
) -> int:
    if phase not in PHASES:
        logger.error("不正なphase: %s（%s）", phase, " / ".join(PHASES))
        return 1

    if phase == "implementation":
        if not file_arg and not dir_arg:
            logger.error("implementationフェーズには --file または --dir が必要です")
            return 1
    else:
        if dir_arg:
            logger.error("--dir は implementation フェーズ専用です（指定フェーズ: %s）", phase)
            return 1
        if not file_arg:
            logger.error("%sフェーズには --file が必要です", phase)
            return 1

    allowed, current_count = check_daily_limit()
    if not allowed:
        logger.error("日次上限超過: %d/%d 回使用済み", current_count, DAILY_CALL_LIMIT)
        payload = {
            "timestamp": datetime.now(JST).isoformat(),
            "phase": phase,
            "target_file": file_arg,
            "target_dir": dir_arg,
            "verdict": "LIMIT_EXCEEDED",
            "judgment": "LIMIT_EXCEEDED",
            "review_text": f"日次上限 {DAILY_CALL_LIMIT} 回に達しました（本日 {current_count} 回使用済み）",
            "model": "gpt-4o+sonnet",
            "gpt_review": "",
            "sonnet_review": "",
            "input_tokens": 0,
            "output_tokens": 0,
            "daily_count": current_count,
            "needs_human_review": False,
        }
        save_result(payload)
        return 2

    target_file: Path | None = None
    target_dir: Path | None = None
    try:
        if file_arg:
            target_file = resolve_path(file_arg)
        if dir_arg:
            target_dir = resolve_dir(dir_arg)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("%s", exc)
        return 1

    anchor = target_file or target_dir
    assert anchor is not None
    tasks_path = resolve_tasks_path(anchor, tasks_arg)
    env = _load_env()
    api_key = env.get("OPENAI_API_KEY", "")
    if not api_key:
        logger.error("OPENAI_API_KEYが設定されていません（config/.env）")
        return 1
    # ANTHROPIC_API_KEYはフォールバック可なので必須チェックしない
    # anthropic_keyはagreement_checker内部で_load_env()して使用

    system_prompt = load_phase_prompt(phase)
    user_prompt = build_user_prompt(phase, target_file, target_dir)

    target_display = str(target_file or target_dir)
    logger.info("ゲートチェック開始: phase=%s target=%s", phase, target_display)

    # 二重ガード第2層: ledger.can_spend（第1層は agreement_checker 内 _cg_allowed で担当）
    _est_in = max(500, len(user_prompt) // 3)
    _est_out = 3000
    if _LEDGER_AVAILABLE:
        try:
            for _model in (REVIEW_MODEL, SONNET_MODEL):
                if not _ledger.can_spend(_est_in, _est_out, _model):
                    logger.error(
                        "CostGuard(ledger): コスト上限超過によりAPI呼び出しを拒否 (phase=%s model=%s)",
                        phase,
                        _model,
                    )
                    _cg_payload: dict[str, Any] = {
                        "timestamp": datetime.now(JST).isoformat(),
                        "phase": phase,
                        "target_file": str(target_file) if target_file else None,
                        "target_dir": str(target_dir) if target_dir else None,
                        "tasks_file": str(tasks_path) if tasks_path else None,
                        "verdict": "COSTGUARD_BLOCKED",
                        "judgment": "COSTGUARD_BLOCKED",
                        "review_text": f"ledger.can_spend()=False: model={_model}",
                        "model": _model,
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "daily_count": current_count,
                        "needs_human_review": False,
                    }
                    save_result(_cg_payload)
                    return 2
        except Exception as exc:
            logger.warning("ledger.can_spend 呼び出し失敗（スキップ）: %s", exc)

    # ── GPT-4o + Sonnet 並列レビュー ──────────────────────────
    try:
        decision = run_dual_review(system_prompt, user_prompt, env)
        if is_ledger_blocked(decision.gpt_result) or is_ledger_blocked(decision.sonnet_result):
            blocked = decision.gpt_result if is_ledger_blocked(decision.gpt_result) else decision.sonnet_result
            logger.error("CostGuard(ledger): API呼び出し前に拒否 model=%s", blocked.model)
            _cg_payload = {
                "timestamp": datetime.now(JST).isoformat(),
                "phase": phase,
                "target_file": str(target_file) if target_file else None,
                "target_dir": str(target_dir) if target_dir else None,
                "tasks_file": str(tasks_path) if tasks_path else None,
                "verdict": "COSTGUARD_BLOCKED",
                "judgment": "COSTGUARD_BLOCKED",
                "review_text": blocked.error or "ledger.can_spend()=False",
                "model": blocked.model,
                "input_tokens": 0,
                "output_tokens": 0,
                "daily_count": current_count,
                "needs_human_review": False,
            }
            save_result(_cg_payload)
            return 2
        review_text = decision.adopted_result.text
        judgment = decision.final_judgment
        verdict = decision.final_verdict
        gpt_text = decision.gpt_result.text
        sonnet_text = decision.sonnet_result.text if decision.sonnet_available else "(Sonnetフォールバック)"
        sonnet_verdict = decision.sonnet_result.verdict
        in_tokens = 0  # agreement_checker内で計上
        out_tokens = 0
        logger.info(
            "2AI合意判定: GPT=%s / Sonnet=%s → %s (%s)",
            decision.gpt_result.judgment,
            decision.sonnet_result.judgment,
            decision.final_judgment,
            "一致" if decision.agreement else "不一致→保守的",
        )
    except Exception as exc:
        logger.error("API呼び出しエラー: %s", exc)
        payload = {
            "timestamp": datetime.now(JST).isoformat(),
            "phase": phase,
            "target_file": str(target_file) if target_file else None,
            "target_dir": str(target_dir) if target_dir else None,
            "tasks_file": str(tasks_path) if tasks_path else None,
            "verdict": "ERROR",
            "judgment": "ERROR",
            "review_text": str(exc),
            "model": "gpt-4o+sonnet",
            "input_tokens": 0,
            "output_tokens": 0,
            "daily_count": current_count,
            "needs_human_review": False,
        }
        save_result(payload)
        return 1

    daily_count = increment_daily_counter()
    human_review = resolve_human_review(verdict, phase, review_text)

    payload: dict[str, Any] = {
        "timestamp": datetime.now(JST).isoformat(),
        "phase": phase,
        "target_file": str(target_file) if target_file else None,
        "target_dir": str(target_dir) if target_dir else None,
        "tasks_file": str(tasks_path) if tasks_path else None,
        "verdict": verdict,
        "judgment": judgment,
        "review_text": review_text,
        "model": "gpt-4o+sonnet",
        "gpt_review": gpt_text,
        "sonnet_review": sonnet_text,
        "sonnet_verdict": sonnet_verdict,
        "input_tokens": in_tokens,
        "output_tokens": out_tokens,
        "daily_count": daily_count,
        "daily_limit": DAILY_CALL_LIMIT,
        "needs_human_review": human_review,
    }

    print(f"\n{'=' * 60}")
    print(f"[GPT-4o]\n{gpt_text}")
    print(f"\n{'─' * 40}")
    print(f"[Sonnet]\n{sonnet_text}")
    print(f"{'=' * 60}")
    print(f"合意判定: {judgment} → verdict={verdict}")
    print(f"松野確認: {'要' if human_review else '不要'}")
    print(f"本日の使用回数: {daily_count}/{DAILY_CALL_LIMIT}")

    target_label = _target_label(file_arg, dir_arg)

    if verdict == "OK":
        if human_review:
            logger.info(
                "松野確認候補だがLINE通知は送らない（verdict=OK, phase=%s, target=%s）",
                phase,
                target_label,
            )
        result_path = save_result(payload)
        print(f"結果JSON: {result_path}")
        return 0

    payload["wall_hitting_file"] = None
    send_line_notification(phase=phase, target=target_label, env=env)
    if not human_review:
        try:
            _, wall_path = run_wall_hitting(review_text, phase, RESULTS_DIR)
            payload["wall_hitting_file"] = str(wall_path)
            print(f"壁打ち結果: {wall_path}")
        except Exception as exc:
            logger.error("壁打ち実行エラー: %s", exc)
            payload["wall_hitting_error"] = str(exc)

    result_path = save_result(payload)
    print(f"結果JSON: {result_path}")

    if tasks_path:
        update_tasks_on_ng(tasks_path, phase)
    return 1


def main() -> None:
    _setup_logging()
    parser = argparse.ArgumentParser(description="自動ダブルチェックシステム（gate_checker）")
    parser.add_argument(
        "--phase",
        required=True,
        choices=list(PHASES),
    )
    parser.add_argument("--file", default=None, help="レビュー対象ファイル")
    parser.add_argument("--dir", default=None, help="レビュー対象ディレクトリ（implementation用）")
    parser.add_argument("--tasks", default=None, help="TASKS.mdパス（省略時は対象と同ディレクトリ）")
    parser.add_argument("--tasks-file", dest="tasks", default=None, help="--tasks の別名")
    args = parser.parse_args()
    sys.exit(run_gate_check(args.phase, args.file, args.dir, args.tasks))


if __name__ == "__main__":
    main()
