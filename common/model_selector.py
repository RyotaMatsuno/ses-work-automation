from __future__ import annotations

import os
import time
from pathlib import Path
from typing import NamedTuple

from common.io_utils import setup_stdout

setup_stdout()

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / "config" / ".env"

try:
    from dotenv import dotenv_values as _dotenv_values

    _ENV: dict = _dotenv_values(ENV_PATH, encoding="utf-8") if ENV_PATH.exists() else {}
except ImportError:
    _ENV = {}


def _get_env(name: str, default: str = "") -> str:
    return os.environ.get(name) or _ENV.get(name, default)


# フェーズ → クラス対応（SPEC §3.1）
PHASE_CLASS: dict[str, str] = {
    "research": "light",
    "requirements": "light",
    "test": "light",
    "design": "medium",
    "pre_impl": "medium",
    "implementation": "heavy",
}

CLASS_DEFAULT_MODEL: dict[str, str] = {
    "light": "gpt-4o-mini",
    "medium": "gpt-5.4",
    "heavy": "codex-5",
}

# クラス別 fallback 候補（models.list で確認）
CLASS_FALLBACKS: dict[str, list[str]] = {
    "light": ["gpt-4o-mini", "gpt-4.1-mini", "gpt-4.1-nano", "gpt-4o"],
    "medium": ["gpt-5.4", "gpt-4.1", "gpt-4o"],
    "heavy": ["codex-5", "gpt-5.4", "gpt-4.1"],
}

# Anthropic モデルプレフィックス（models.list をスキップして直接使用）
_ANTHROPIC_PREFIXES = ("claude", "anthropic")

# モデル一覧キャッシュ（set, timestamp）
_models_cache: tuple[set[str], float] | None = None
_CACHE_TTL_SEC = 300.0
_consecutive_failures = 0


class ModelSelection(NamedTuple):
    model: str
    model_class: str
    fallback: bool
    unknown_model: bool


class ModelSelectionError(RuntimeError):
    def __init__(self, reason: str, detail: str = ""):
        super().__init__(reason)
        self.reason = reason
        self.detail = detail


def _is_anthropic_model(model: str) -> bool:
    lower = model.lower()
    return any(lower.startswith(p) for p in _ANTHROPIC_PREFIXES)


def _check_anthropic_available(model: str) -> bool:
    """Anthropic models.list() で存在確認（失敗時は True として続行）。"""
    try:
        import anthropic as _anth

        api_key = _get_env("ANTHROPIC_API_KEY", "")
        client = _anth.Anthropic(api_key=api_key)
        result = client.models.list(limit=100)
        available = {m.id for m in result.data}
        return model in available
    except Exception:
        return True  # 確認失敗時は利用可と見なす


def _fetch_openai_models() -> set[str]:
    """OpenAI models.list() を呼んで利用可能モデルセットを返す。失敗時は RuntimeError。"""
    try:
        import openai as _oai
    except ImportError as e:
        raise RuntimeError(f"openai library not available: {e}")

    api_key = _get_env("OPENAI_API_KEY", "")
    client = _oai.OpenAI(api_key=api_key)

    delays = [1, 3]
    last_err: Exception | None = None
    for i in range(3):
        try:
            result = client.models.list()
            return {m.id for m in result.data}
        except Exception as e:
            last_err = e
            if i < len(delays):
                time.sleep(delays[i])
    raise RuntimeError(f"models.list() failed after retries: {last_err}")


def _get_available_models() -> set[str]:
    global _models_cache
    now = time.monotonic()
    if _models_cache and (now - _models_cache[1]) < _CACHE_TTL_SEC:
        return _models_cache[0]
    models = _fetch_openai_models()
    _models_cache = (models, now)
    return models


def _phase_default_model(phase: str) -> str:
    key = f"PHASE_MODEL_{phase.upper()}"
    env_val = _get_env(key, "")
    if env_val:
        return env_val
    cls = PHASE_CLASS.get(phase, "light")
    return CLASS_DEFAULT_MODEL.get(cls, "gpt-4o-mini")


def select_model(phase: str, model_hint: str | None = None) -> ModelSelection:
    """フェーズとオプションの model_hint から (model, model_class, fallback, unknown_model) を返す。

    失敗時は ModelSelectionError を raise する:
      - reason="error_transient_models_list": models.list() 全失敗
      - reason="error_model_unavailable_all_fallback": 同クラス代替も不在
    """
    global _consecutive_failures

    model_class = PHASE_CLASS.get(phase, "light")

    # Anthropic モデルは別経路で処理
    if model_hint and _is_anthropic_model(model_hint):
        available = _check_anthropic_available(model_hint)
        if available:
            _consecutive_failures = 0
            return ModelSelection(
                model=model_hint,
                model_class=model_class,
                fallback=False,
                unknown_model=False,
            )
        # Anthropic モデル不在: 通常解決にフォールバック（警告ログ）
        import logging

        logging.getLogger(__name__).warning("model_hint %s not available, falling back to phase default", model_hint)
        model_hint = None

    # models.list() 取得（リトライ付き）
    try:
        available = _get_available_models()
        _consecutive_failures = 0
    except RuntimeError as e:
        _consecutive_failures += 1
        if _consecutive_failures >= 3:
            from common.notifier import notify

            try:
                notify("error_transient_models_list", phase=phase)
            except Exception:
                pass
        raise ModelSelectionError("error_transient_models_list") from e

    # model_hint が指定されていて利用可能ならそれを使用
    if model_hint:
        if model_hint in available:
            return ModelSelection(
                model=model_hint,
                model_class=model_class,
                fallback=False,
                unknown_model=False,
            )
        import logging

        logging.getLogger(__name__).warning("model_hint %s not in available models, falling back", model_hint)

    # フェーズデフォルトモデル
    target = _phase_default_model(phase)

    if target in available:
        return ModelSelection(
            model=target,
            model_class=model_class,
            fallback=False,
            unknown_model=False,
        )

    # 同クラス内 fallback 候補
    for candidate in CLASS_FALLBACKS.get(model_class, []):
        if candidate in available and candidate != target:
            import logging

            logging.getLogger(__name__).warning(
                "Model %s not available, using fallback %s (class=%s)", target, candidate, model_class
            )
            return ModelSelection(
                model=candidate,
                model_class=model_class,
                fallback=True,
                unknown_model=False,
            )

    raise ModelSelectionError("error_model_unavailable_all_fallback")
