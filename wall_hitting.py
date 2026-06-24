# -*- coding: utf-8 -*-
"""OpenAI/Gemini wall-hitting helper."""

import argparse
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import dotenv_values

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / "config" / ".env"

# CostGuard
try:
    import sys as _sys

    _sys.path.insert(0, str(BASE_DIR))
    from common.ledger import can_spend
    from common.ledger import record as ledger_record

    _LEDGER_AVAILABLE = True
except Exception:
    _LEDGER_AVAILABLE = False
    can_spend = None
    ledger_record = None

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
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
    parser = argparse.ArgumentParser(description="GPT-4o/Gemini 2.0 Flashに技術相談する壁打ちスクリプト")
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
    from common.ledger import daily_total

    total = daily_total()
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


def fetch_openai(problem: str, api_key: str, model: str) -> str:
    if not api_key:
        return "OpenAI APIキー未設定"

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
        return compact_text(content)
    except requests.RequestException as exc:
        return f"OpenAI取得失敗: {exc}"
    except (KeyError, IndexError, ValueError) as exc:
        return f"OpenAI応答解析失敗: {exc}"


def fetch_gemini(problem: str, api_key: str) -> str:
    if not api_key:
        return "Gemini APIキー未設定"

    payload = {
        "contents": [{"parts": [{"text": (f"{COMMON_SYSTEM_PROMPT}\n{GEMINI_EXTRA_PROMPT}\n\n問題:\n{problem}")}]}],
        "generationConfig": {"maxOutputTokens": 500},
    }
    params = {"key": api_key}

    for attempt in range(2):
        try:
            response = requests.post(GEMINI_URL, params=params, json=payload, timeout=TIMEOUT_SECONDS)
            if response.status_code == 429 and attempt == 0:
                time.sleep(10)
                continue
            if response.status_code == 429:
                return "Gemini一時利用不可（レート制限）"
            response.raise_for_status()
            data = response.json()
            content = data["candidates"][0]["content"]["parts"][0]["text"]
            return compact_text(content)
        except requests.RequestException as exc:
            return f"Gemini取得失敗: {exc}"
        except (KeyError, IndexError, ValueError) as exc:
            return f"Gemini応答解析失敗: {exc}"

    return "Gemini一時利用不可"


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
    args = parse_args()
    problem = clamp_problem(args.problem)

    # 週末キャップチェック
    if not _check_weekend_cap():
        print("週末の日次コスト上限($2)に達したため壁打ちをスキップします。")
        return 1

    # CostGuard 事前チェック（推定: GPT 300in/500out + Gemini 300in/500out）
    if _LEDGER_AVAILABLE and can_spend is not None:
        if not can_spend(600, 1000, "gpt-4o"):
            print("[wall_hitting] CostGuard: 日次/月次上限によりスキップ")
            return 1

    openai_key, gemini_key = load_api_keys()

    openai_model = SEARCH_OPENAI_MODEL if args.search else DEFAULT_OPENAI_MODEL
    openai_response = fetch_openai(problem, openai_key, openai_model)
    gemini_response = fetch_gemini(problem, gemini_key)

    # CostGuard 事後記録
    if _LEDGER_AVAILABLE and ledger_record is not None:
        try:
            ledger_record(300, 500, "gpt-4o", "wall_hitting_openai")
            ledger_record(300, 500, "gemini-2.5-flash", "wall_hitting_gemini")
        except Exception:
            pass

    print(format_result(problem, openai_response, gemini_response))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
