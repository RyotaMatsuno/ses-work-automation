# -*- coding: utf-8 -*-
"""
wall_hitting.py — GPT-4o / Gemini 2.5 Flash 壁打ちスクリプト

【仕様概要】
- 技術的問題をGPT-4o（実装最短パス）とGemini 2.5 Flash（アーキ観点）に同時相談
- --search フラグで gpt-4o-search-preview（Web検索付き）に切替可能
- CostGuard: can_spend で呼び出し前チェック、record で成功後に実トークン記録
- 週末専用日次キャップ: $2（WEEKEND_DAILY_LIMIT_USD）
- LLM_KILL=1 で全LLM呼び出しを即時停止
- common.ledger インポート失敗時は SystemExit(1) で実行停止（フェイルクローズ）

【コスト推定値】
- 通常モード (gpt-4o): in=300 / out=500 トークン
- 検索モード (gpt-4o-search-preview): in=1000 / out=1500 トークン（Web検索分を加算）
- Gemini 2.5 Flash: in=300 / out=500 トークン

【依存】
- common.ledger: can_spend / record / daily_total
- requests, python-dotenv
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import requests
from dotenv import dotenv_values

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / "config" / ".env"

# CostGuard（インポート失敗時は実行停止: CLAUDE.md「CostGuardなしでLLMを呼び出す」禁止）
try:
    sys.path.insert(0, str(BASE_DIR))
    from common.ledger import can_spend
    from common.ledger import daily_total as _daily_total
    from common.ledger import record as ledger_record

    _LEDGER_AVAILABLE = True
except Exception as _ledger_exc:
    print(
        f"[wall_hitting] FATAL: CostGuard(common.ledger)インポート失敗 → 実行停止: {_ledger_exc}",
        file=sys.stderr,
    )
    raise SystemExit(1)

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
DEFAULT_OPENAI_MODEL = "gpt-4o"
WEEKEND_DAILY_LIMIT_USD = 2.0  # 週末専用日次キャップ
SEARCH_OPENAI_MODEL = "gpt-4o-search-preview"
TIMEOUT_SECONDS = 60
MAX_PROBLEM_CHARS = 500

COMMON_SYSTEM_PROMPT = (
    "あなたはPythonシステム開発の専門家です。\n"
    "以下の技術的問題について、300文字以内で具体的な解決策を提案してください。\n"
    "コードスニペットがあれば含めてください。"
)
OPENAI_EXTRA_PROMPT = "速度・シンプルさを最優先に、最短の修正パスを示してください。"
GEMINI_EXTRA_PROMPT = "長期保守性・拡張性を重視し、アーキテクチャ観点から助言してください。"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GPT-4o/Gemini 2.5 Flashに技術相談する壁打ちスクリプト")
    parser.add_argument("--problem", required=True, help="問題の説明（500文字以内）")
    parser.add_argument("--search", action="store_true", help="OpenAIを検索対応モデルで実行")
    return parser.parse_args()


def _is_weekend() -> bool:
    """土日判定"""
    return datetime.now().weekday() >= 5  # 5=土, 6=日


def _check_weekend_cap() -> bool:
    """
    週末の場合のみ日次キャップ $2 をチェック。
    キャップを超えていたら False を返す。
    平日は常に True。
    """
    if not _is_weekend():
        return True
    if not _LEDGER_AVAILABLE:
        return True
    total = _daily_total()
    if total >= WEEKEND_DAILY_LIMIT_USD:
        print(f"[wall_hitting] 週末日次キャップ超過 (${total:.4f} >= ${WEEKEND_DAILY_LIMIT_USD})")
        return False
    return True


def load_api_keys() -> tuple[str, str]:
    config = dotenv_values(ENV_PATH)
    return config.get("OPENAI_API_KEY", "") or "", config.get("GEMINI_API_KEY", "") or ""


def clamp_problem(problem: str) -> str:
    problem = problem.strip()
    if len(problem) <= MAX_PROBLEM_CHARS:
        return problem
    return problem[:MAX_PROBLEM_CHARS]


def compact_text(value: str) -> str:
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    return "\n".join(lines).strip() or "応答本文なし"


def fetch_openai(problem: str, api_key: str, model: str) -> tuple[str, int, int]:
    if not api_key:
        return "OpenAI APIキー未設定", 0, 0

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": COMMON_SYSTEM_PROMPT},
            {"role": "user", "content": f"{OPENAI_EXTRA_PROMPT}\n\n問題:\n{problem}"},
        ],
        "max_tokens": 500,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(OPENAI_URL, headers=headers, json=payload, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        in_tok = int(usage.get("prompt_tokens", 0))
        out_tok = int(usage.get("completion_tokens", 0))
        return compact_text(content), in_tok, out_tok
    except requests.RequestException as exc:
        return f"OpenAI取得失敗: {exc}", 0, 0
    except (KeyError, IndexError, ValueError) as exc:
        return f"OpenAI応答解析失敗: {exc}", 0, 0


def fetch_gemini(problem: str, api_key: str) -> tuple[str, int, int]:
    if not api_key:
        return "Gemini APIキー未設定", 0, 0

    payload = {
        "contents": [{"parts": [{"text": (f"{COMMON_SYSTEM_PROMPT}\n{GEMINI_EXTRA_PROMPT}\n\n問題:\n{problem}")}]}],
        "generationConfig": {"maxOutputTokens": 500},
    }
    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}

    for attempt in range(2):
        try:
            response = requests.post(GEMINI_URL, headers=headers, json=payload, timeout=TIMEOUT_SECONDS)
            if response.status_code == 429 and attempt == 0:
                time.sleep(10)
                continue
            if response.status_code == 429:
                return "Gemini一時利用不可（レート制限）", 0, 0
            response.raise_for_status()
            data = response.json()
            content = data["candidates"][0]["content"]["parts"][0]["text"]
            usage = data.get("usageMetadata", {})
            in_tok = int(usage.get("promptTokenCount", 0))
            out_tok = int(usage.get("candidatesTokenCount", 0))
            return compact_text(content), in_tok, out_tok
        except requests.RequestException as exc:
            if attempt == 0:
                continue
            return f"Gemini取得失敗: {exc}", 0, 0
        except (KeyError, IndexError, ValueError) as exc:
            return f"Gemini応答解析失敗: {exc}", 0, 0

    return "Gemini一時利用不可", 0, 0


GEMINI_FAIL_PREFIXES = (
    "Gemini取得失敗",
    "Gemini応答解析失敗",
    "Gemini APIキー未設定",
    "Gemini一時利用不可",
)
OPENAI_FAIL_PREFIXES = (
    "OpenAI取得失敗",
    "OpenAI応答解析失敗",
    "OpenAI APIキー未設定",
)

_MODEL_RATES_PATH = BASE_DIR / "config" / "model_rates.json"
_KNOWN_MODELS_CACHE: set[str] | None = None


def _is_model_known(model: str) -> bool:
    """ledger単価表(model_rates.json)にモデルが存在するか確認（部分一致含む）。"""
    global _KNOWN_MODELS_CACHE
    if _KNOWN_MODELS_CACHE is None:
        try:
            rates = json.loads(_MODEL_RATES_PATH.read_text(encoding="utf-8"))
            _KNOWN_MODELS_CACHE = set(rates.keys())
        except Exception:
            return True  # 読み込み失敗時はfail-open
    model_key = (model or "").lower()
    for k in _KNOWN_MODELS_CACHE:
        if k.lower() in model_key or model_key in k.lower():
            return True
    return False


def _build_can_spend_est(problem: str, model: str, max_tokens: int) -> tuple[int, int]:
    """can_spend用のest_in/est_outを動的算出。
    - est_in: max(500, len(problem)//3)
    - search系モデル: 1.5倍保守係数
    - ledger未知モデル: WARNINGログ + 2倍保守係数
    """
    est_in = max(500, len(problem) // 3)
    est_out = max_tokens
    if "search" in model.lower():
        return int(est_in * 1.5), int(est_out * 1.5)
    if not _is_model_known(model):
        print(
            f"[wall_hitting] WARNING: 未知モデル '{model}' → コスト見積もりを2倍で保守計算",
            file=sys.stderr,
        )
        return est_in * 2, est_out * 2
    return est_in, est_out


def _response_succeeded(response: str, fail_prefixes: tuple[str, ...]) -> bool:
    return not any(response.startswith(prefix) for prefix in fail_prefixes)


def _record_llm_usage(
    in_tokens: int,
    out_tokens: int,
    model: str,
    *,
    est_in: int = 300,
    est_out: int = 500,
) -> None:
    if not _LEDGER_AVAILABLE or ledger_record is None:
        return
    try:
        ledger_record(
            in_tokens or est_in,
            out_tokens or est_out,
            model,
            "wall_hitting.py",
            phase="wallhit",
        )
    except Exception as exc:
        print(f"[wall_hitting] 警告: ledger.record失敗: {exc}", file=sys.stderr)


def format_result(problem: str, openai_response: str, gemini_response: str) -> str:
    return f"""====== 壁打ち結果 ======

【問題】
{problem}

【GPT-4o視点（実装最短パス）】
{openai_response}

【Gemini視点（アーキテクチャ・長期保守）】
{gemini_response}

【ジョブズ判断メモ欄】
（ここに自分の判断を書く）
========================"""


def main() -> int:
    if os.environ.get("LLM_KILL") == "1":
        print("[wall_hitting] LLM_KILL=1 により実行停止", file=sys.stderr)
        return 1

    args = parse_args()
    problem = clamp_problem(args.problem)

    # 週末キャップチェック
    if not _check_weekend_cap():
        print("週末の日次コスト上限($2)に達したため壁打ちをスキップします。")
        return 1

    openai_model = SEARCH_OPENAI_MODEL if args.search else DEFAULT_OPENAI_MODEL

    # CostGuard 事前チェック（動的est_in + searchは1.5x + 未知モデルは2x）
    if can_spend is None:
        print("[wall_hitting] FATAL: can_spend が None → 実行停止", file=sys.stderr)
        return 1
    est_in_openai, est_out_openai = _build_can_spend_est(problem, openai_model, 500)
    est_in_gemini, est_out_gemini = _build_can_spend_est(problem, GEMINI_MODEL, 500)
    if not can_spend(est_in_openai, est_out_openai, openai_model) or not can_spend(est_in_gemini, est_out_gemini, GEMINI_MODEL):
        print("[wall_hitting] CostGuard: 日次/月次上限によりスキップ")
        return 1

    openai_key, gemini_key = load_api_keys()
    openai_response, openai_in, openai_out = fetch_openai(problem, openai_key, openai_model)
    gemini_response, gemini_in, gemini_out = fetch_gemini(problem, gemini_key)

    # CostGuard 事後記録（成功したLLM呼び出しのみ。実トークン優先、取得不能時は推定値）
    if _response_succeeded(openai_response, OPENAI_FAIL_PREFIXES):
        _record_llm_usage(openai_in, openai_out, openai_model, est_in=est_in_openai, est_out=est_out_openai)
    if _response_succeeded(gemini_response, GEMINI_FAIL_PREFIXES):
        _record_llm_usage(gemini_in, gemini_out, GEMINI_MODEL, est_in=est_in_gemini, est_out=est_out_gemini)

    print(format_result(problem, openai_response, gemini_response))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
