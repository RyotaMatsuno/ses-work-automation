#!/usr/bin/env python3
"""GPT-4o + Claude Sonnet の合意判定共通ライブラリ。
gate_checker と auto_bug_watcher の両方から import して使う。
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_SES_WORK = Path(__file__).resolve().parent.parent

if str(_SES_WORK) not in sys.path:
    sys.path.insert(0, str(_SES_WORK))
from cost_guard import allowed as _cg_allowed
from cost_guard import finalize as _cg_finalize

try:
    from common import ledger as _ledger

    _LEDGER_AVAILABLE = True
except ImportError:
    _ledger = None  # type: ignore[assignment]
    _LEDGER_AVAILABLE = False

LEDGER_BLOCKED_MARKER = "LedgerBlocked"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent
SES_WORK = BASE_DIR.parent

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
SONNET_MODEL = "claude-sonnet-4-6"
GATE_CHECKER_BLOCK_TYPE = "gate_check"
GPT_PHASE = "gate"
SONNET_PHASE = "review_sonnet"
SCRIPT_NAME = "gate_check.py"  # CostGuard・ledger 共通（SPEC §7）
TIMEOUT_SECONDS = 90
SONNET_MAX_TOKENS = 3000

logger = logging.getLogger("agreement_checker")


@dataclass
class ModelResult:
    model: str  # "gpt-4o" | "sonnet"
    text: str  # 生のレスポンス全文
    verdict: str  # "OK" | "NG" | "ERROR"
    judgment: str  # "GO" | "条件付きGO" | "NG" | "ERROR"
    confidence: float = 1.0
    error: str = ""


@dataclass
class AgreementDecision:
    final_verdict: str  # "OK" | "NG"
    final_judgment: str  # "GO" | "条件付きGO" | "NG"
    adopted_model: str  # どちらの案を採用したか
    adopted_result: ModelResult = field(default_factory=lambda: ModelResult("", "", "", ""))
    gpt_result: ModelResult = field(default_factory=lambda: ModelResult("", "", "", ""))
    sonnet_result: ModelResult = field(default_factory=lambda: ModelResult("", "", "", ""))
    sonnet_available: bool = True
    agreement: bool = True  # 両者が一致したか
    reason: str = ""  # 不一致理由など


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


def _target_id(user_prompt: str, suffix: str = "") -> str:
    raw = f"{suffix}:{user_prompt[:500]}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _ledger_can_spend(est_in: int, est_out: int, model: str) -> bool:
    if not _LEDGER_AVAILABLE:
        return True
    try:
        return _ledger.can_spend(est_in, est_out, model)
    except Exception as exc:
        logger.warning("ledger.can_spend 呼び出し失敗（スキップ）: %s", exc)
        return True


def _ledger_record(in_tokens: int, out_tokens: int, model: str) -> None:
    if not _LEDGER_AVAILABLE:
        return
    try:
        _ledger.record(in_tokens, out_tokens, model, SCRIPT_NAME, phase="gate")
    except Exception as exc:
        logger.warning("ledger.record 呼び出し失敗: %s", exc)


def is_ledger_blocked(result: ModelResult) -> bool:
    return result.verdict == "ERROR" and LEDGER_BLOCKED_MARKER in (result.error or "")


def parse_judgment(review_text: str) -> tuple[str, str]:
    """レビュー本文から判定を抽出。戻り値: (judgment, verdict)"""
    patterns = [
        r"【判定[:：]\s*(GO|条件付きGO|NG)】",
        r"判定[:：]\s*(GO|条件付きGO|NG)",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, review_text, flags=re.IGNORECASE)
        if matches:
            raw = matches[0]  # 先頭判定優先（1行目判定プロンプト対応）
            if "条件付き" in raw:
                return "条件付きGO", "OK"
            if raw.upper() == "GO":
                return "GO", "OK"
            if raw.upper() == "NG":
                return "NG", "NG"
    upper = review_text.upper()
    if "【判定: NG】" in review_text or "判定: NG" in upper:
        return "NG", "NG"
    if "条件付きGO" in review_text:
        return "条件付きGO", "OK"
    if "【判定: GO】" in review_text or re.search(r"判定[:：]\s*GO", review_text):
        return "GO", "OK"
    for chunk in (review_text.strip()[:200], review_text.strip()[-200:]):
        if re.search(r'[""]?(条件付きGO)[""]?', chunk):
            return "条件付きGO", "OK"
        if re.search(r'[""]?(NG)[""]?', chunk):
            return "NG", "NG"
        if re.search(r'[""]?(GO)[""]?(?:\s|$|[。）)])', chunk) and "条件付き" not in chunk:
            return "GO", "OK"
    return "UNKNOWN", "NG"


def _extract_sonnet_text(data: dict[str, Any]) -> str:
    """Anthropic Messages APIレスポンスからテキストを安全に抽出。"""
    content = data.get("content") or []
    texts = [
        block.get("text", "")
        for block in content
        if isinstance(block, dict) and block.get("type") == "text" and block.get("text")
    ]
    text = "\n".join(t.strip() for t in texts if t.strip())
    if not text:
        stop_reason = data.get("stop_reason", "unknown")
        raise ValueError(f"Sonnet空レスポンス (stop_reason={stop_reason})")
    return text


def call_sonnet(system_prompt: str, user_prompt: str, api_key: str) -> ModelResult:
    """Claude Sonnet 4.6 でレビューを実行。"""
    if not api_key:
        return ModelResult("sonnet", "", "ERROR", "ERROR", error="ANTHROPIC_API_KEY未設定")

    est_in = len(user_prompt) // 4 + len(system_prompt) // 4 + 200
    est_out = SONNET_MAX_TOKENS
    if not _ledger_can_spend(est_in, est_out, SONNET_MODEL):
        return ModelResult(
            "sonnet",
            "",
            "ERROR",
            "ERROR",
            error=f"{LEDGER_BLOCKED_MARKER}: ledger.can_spend()=False",
        )

    decision = _cg_allowed(
        phase=SONNET_PHASE,
        block_type=GATE_CHECKER_BLOCK_TYPE,
        target_id=_target_id(user_prompt, "sonnet"),
        est_in=est_in,
        est_out=est_out,
        model_hint=SONNET_MODEL,
        script=SCRIPT_NAME,
    )
    if not decision.allowed:
        return ModelResult(
            "sonnet",
            "",
            "ERROR",
            "ERROR",
            error=f"CostGuard blocked: {decision.reason}",
        )

    payload = {
        "model": SONNET_MODEL,
        "max_tokens": SONNET_MAX_TOKENS,
        "temperature": 0,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    error_kind = ""
    in_tok = 0
    out_tok = 0
    result: ModelResult | None = None

    try:
        for attempt in range(3):
            try:
                req = urllib.request.Request(
                    ANTHROPIC_URL,
                    data=body,
                    headers={
                        "Content-Type": "application/json",
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
                    raw_body = resp.read().decode("utf-8")
                    data = json.loads(raw_body)
                text = _extract_sonnet_text(data)
                usage = data.get("usage", {})
                in_tok = int(usage.get("input_tokens", 0))
                out_tok = int(usage.get("output_tokens", 0))
                judgment, verdict = parse_judgment(text)
                result = ModelResult("sonnet", text, verdict, judgment)
                _ledger_record(in_tok, out_tok, SONNET_MODEL)
                break
            except urllib.error.HTTPError as e:
                body_str = e.read().decode("utf-8", errors="replace")[:500]
                logger.error("Sonnet HTTPエラー: status=%s body=%s", e.code, body_str)
                if e.code == 429 and attempt < 2:
                    time.sleep(10)
                    continue
                error_kind = "permanent_api"
                result = ModelResult("sonnet", "", "ERROR", "ERROR", error=f"HTTP {e.code}: {body_str}")
                break
            except urllib.error.URLError as exc:
                # タイムアウト（socket.timeout）含む。リトライしない
                logger.error("Sonnet URLError（タイムアウト含む、リトライなし）: %s", exc)
                error_kind = "transient"
                result = ModelResult("sonnet", "", "ERROR", "ERROR", error=f"URLError: {exc}")
                break
            except Exception as exc:
                logger.error("Sonnet呼び出し失敗: %s", exc)
                error_kind = "transient"
                result = ModelResult("sonnet", "", "ERROR", "ERROR", error=str(exc))
                break

        if result is None:
            error_kind = error_kind or "transient"
            result = ModelResult("sonnet", "", "ERROR", "ERROR", error="Sonnet一時利用不可")
        return result
    finally:
        if decision.allowed:
            try:
                _cg_finalize(
                    decision,
                    in_tokens=in_tok,
                    out_tokens=out_tok,
                    success=(error_kind == "" and result is not None and result.verdict != "ERROR"),
                    error_kind=error_kind,
                )
            except Exception:
                pass


def call_gpt4o_simple(system_prompt: str, user_prompt: str, api_key: str) -> ModelResult:
    """GPT-4o でレビューを実行（cost_guard.allowed()/finalize() 経由）。"""
    if not api_key:
        return ModelResult("gpt-4o", "", "ERROR", "ERROR", error="OPENAI_API_KEY未設定")

    est_in = max(500, len(user_prompt) // 3 + len(system_prompt) // 3)
    est_out = 3000
    gpt_model = "gpt-4o"
    if not _ledger_can_spend(est_in, est_out, gpt_model):
        return ModelResult(
            "gpt-4o",
            "",
            "ERROR",
            "ERROR",
            error=f"{LEDGER_BLOCKED_MARKER}: ledger.can_spend()=False",
        )

    decision = _cg_allowed(
        phase=GPT_PHASE,
        block_type=GATE_CHECKER_BLOCK_TYPE,
        target_id=_target_id(user_prompt, "gpt"),
        est_in=est_in,
        est_out=est_out,
        model_hint=gpt_model,
        script=SCRIPT_NAME,
    )
    if not decision.allowed:
        return ModelResult(
            "gpt-4o",
            "",
            "ERROR",
            "ERROR",
            error=f"CostGuard blocked: {decision.reason}",
        )

    payload = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": 3000,
        "temperature": 0,
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    error_kind = ""
    in_tok = 0
    out_tok = 0
    result: ModelResult | None = None

    try:
        for attempt in range(3):
            try:
                req = urllib.request.Request(
                    OPENAI_URL,
                    data=body,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                text = data["choices"][0]["message"]["content"] or ""
                usage = data.get("usage", {})
                in_tok = int(usage.get("prompt_tokens", 0) or est_in)
                out_tok = int(usage.get("completion_tokens", 0) or est_out)
                judgment, verdict = parse_judgment(text)
                result = ModelResult("gpt-4o", text, verdict, judgment)
                _ledger_record(in_tok, out_tok, gpt_model)
                break
            except urllib.error.HTTPError as e:
                body_str = e.read().decode("utf-8", errors="replace")[:200]
                if e.code == 429 and attempt < 2:
                    time.sleep(2**attempt)
                    continue
                error_kind = "permanent_api"
                result = ModelResult("gpt-4o", "", "ERROR", "ERROR", error=f"HTTP {e.code}: {body_str}")
                break
            except urllib.error.URLError as exc:
                # タイムアウト（socket.timeout）含む。リトライしない
                logger.error("GPT URLError（タイムアウト含む、リトライなし）: %s", exc)
                error_kind = "transient"
                result = ModelResult("gpt-4o", "", "ERROR", "ERROR", error=f"URLError: {exc}")
                break
            except Exception as exc:
                error_kind = "transient"
                result = ModelResult("gpt-4o", "", "ERROR", "ERROR", error=str(exc))
                break
        if result is None:
            error_kind = error_kind or "transient"
            result = ModelResult("gpt-4o", "", "ERROR", "ERROR", error="API呼び出し失敗")
        return result
    finally:
        if decision.allowed:
            try:
                _cg_finalize(
                    decision,
                    in_tokens=in_tok,
                    out_tokens=out_tok,
                    success=(error_kind == "" and result is not None and result.verdict != "ERROR"),
                    error_kind=error_kind,
                )
            except Exception:
                pass


def judge(
    gpt_result: ModelResult,
    sonnet_result: ModelResult,
) -> AgreementDecision:
    """
    GPT-4o と Sonnet の結果を合意判定して AgreementDecision を返す。

    合意ルール:
      両者 GO/条件付きGO → GO（GPT採用）
      両者 NG             → NG（GPT採用）
      片方 NG             → NG（保守的、NG側採用）
      Sonnet ERROR        → GPT単独判定にフォールバック
      GPT ERROR           → Sonnet単独判定にフォールバック
      両者 ERROR          → NG（保守的）
    """
    if sonnet_result.verdict == "ERROR" and gpt_result.verdict == "ERROR":
        return AgreementDecision(
            final_verdict="NG",
            final_judgment="NG",
            adopted_model="両者エラー",
            adopted_result=gpt_result,
            gpt_result=gpt_result,
            sonnet_result=sonnet_result,
            sonnet_available=False,
            agreement=False,
            reason=f"両者エラー → 保守的NG: GPT={gpt_result.error} / Sonnet={sonnet_result.error}",
        )

    if sonnet_result.verdict == "ERROR":
        return AgreementDecision(
            final_verdict=gpt_result.verdict if gpt_result.verdict != "ERROR" else "NG",
            final_judgment=gpt_result.judgment if gpt_result.judgment != "ERROR" else "NG",
            adopted_model="gpt-4o（Sonnetフォールバック）",
            adopted_result=gpt_result,
            gpt_result=gpt_result,
            sonnet_result=sonnet_result,
            sonnet_available=False,
            agreement=False,
            reason=f"Sonnetエラーのためフォールバック: {sonnet_result.error}",
        )

    if gpt_result.verdict == "ERROR":
        return AgreementDecision(
            final_verdict=sonnet_result.verdict,
            final_judgment=sonnet_result.judgment,
            adopted_model="sonnet（GPTフォールバック）",
            adopted_result=sonnet_result,
            gpt_result=gpt_result,
            sonnet_result=sonnet_result,
            sonnet_available=True,
            agreement=False,
            reason=f"GPTエラーのためSonnetフォールバック: {gpt_result.error}",
        )

    gpt_ok = gpt_result.verdict == "OK"
    sonnet_ok = sonnet_result.verdict == "OK"

    if gpt_ok == sonnet_ok:
        adopted = gpt_result
        final_verdict = gpt_result.verdict
        if gpt_ok:
            if gpt_result.judgment == "条件付きGO" or sonnet_result.judgment == "条件付きGO":
                final_judgment = "条件付きGO"
            else:
                final_judgment = "GO"
        else:
            final_judgment = "NG"
        return AgreementDecision(
            final_verdict=final_verdict,
            final_judgment=final_judgment,
            adopted_model="gpt-4o（両者一致）",
            adopted_result=adopted,
            gpt_result=gpt_result,
            sonnet_result=sonnet_result,
            sonnet_available=True,
            agreement=True,
            reason="両者一致",
        )

    if not gpt_ok:
        adopted = gpt_result
        adopted_model = "gpt-4o（不一致・保守的）"
    else:
        adopted = sonnet_result
        adopted_model = "sonnet（不一致・保守的）"

    return AgreementDecision(
        final_verdict="NG",
        final_judgment="NG",
        adopted_model=adopted_model,
        adopted_result=adopted,
        gpt_result=gpt_result,
        sonnet_result=sonnet_result,
        sonnet_available=True,
        agreement=False,
        reason=f"不一致（GPT:{gpt_result.judgment} / Sonnet:{sonnet_result.judgment}）→ 保守的NG採用",
    )


def run_dual_review(
    system_prompt: str,
    user_prompt: str,
    env: dict[str, str] | None = None,
) -> AgreementDecision:
    """
    GPT-4o + Sonnet を並列実行して AgreementDecision を返すメイン関数。
    gate_check.py と auto_bug_watcher/classifier.py から呼ぶ。
    """
    if env is None:
        env = _load_env()

    openai_key = env.get("OPENAI_API_KEY", "")
    anthropic_key = env.get("ANTHROPIC_API_KEY", "")

    with ThreadPoolExecutor(max_workers=2) as executor:
        fut_gpt = executor.submit(call_gpt4o_simple, system_prompt, user_prompt, openai_key)
        fut_sonnet = executor.submit(call_sonnet, system_prompt, user_prompt, anthropic_key)

        gpt_result = fut_gpt.result()
        sonnet_result = fut_sonnet.result()

    return judge(gpt_result, sonnet_result)
