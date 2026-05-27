# -*- coding: utf-8 -*-
"""OpenAI/Gemini wall-hitting helper."""

import argparse
import time
from pathlib import Path

import requests
from dotenv import dotenv_values


BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / "config" / ".env"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
DEFAULT_OPENAI_MODEL = "gpt-4o"
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
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            f"{COMMON_SYSTEM_PROMPT}\n"
                            f"{GEMINI_EXTRA_PROMPT}\n\n"
                            f"問題:\n{problem}"
                        )
                    }
                ]
            }
        ],
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
    openai_key, gemini_key = load_api_keys()

    openai_model = SEARCH_OPENAI_MODEL if args.search else DEFAULT_OPENAI_MODEL
    openai_response = fetch_openai(problem, openai_key, openai_model)
    gemini_response = fetch_gemini(problem, gemini_key)
    print(format_result(problem, openai_response, gemini_response))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
