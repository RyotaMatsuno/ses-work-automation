"""skill_pre_normalize unit tests."""

from __future__ import annotations

import sys
from pathlib import Path

MATCHING_V3_DIR = Path(__file__).resolve().parents[1]
if str(MATCHING_V3_DIR) not in sys.path:
    sys.path.insert(0, str(MATCHING_V3_DIR))

from skill_pre_normalize import pre_normalize_skill_text, pre_normalize_skill_tokens, skill_lookup_key


def test_fullwidth_java():
    assert pre_normalize_skill_text("Ｊａｖａ") == "Java"


def test_katakana_python():
    assert pre_normalize_skill_text("パイソン") == "Python"


def test_csharp_variants():
    assert pre_normalize_skill_text("C＃") == "C#"
    assert pre_normalize_skill_text("c sharp") == "C#"


def test_node_variants():
    assert pre_normalize_skill_text("NodeJS") == "Node.js"
    assert pre_normalize_skill_text("node js") == "Node.js"


def test_vb_net_spacing():
    assert pre_normalize_skill_text("VB . NET") == "VB.NET"
    assert pre_normalize_skill_text("VB・NET") == "VB.NET"


def test_ops_suffix_strip():
    assert pre_normalize_skill_text("Azure運用保守") == "Azure"
    assert pre_normalize_skill_text("Databricks運用保守") == "Databricks"


def test_lookup_key():
    assert skill_lookup_key("  Java  ") == "java"
    assert skill_lookup_key("NodeJS") == "node.js"


# ── pre_normalize_skill_tokens: 2トークン化ケース ────────────────


def test_tokens_ops_suffix_2token():
    """Linux運用保守 → [Linux, 運用保守] の2トークン。"""
    assert pre_normalize_skill_tokens("Linux運用保守") == ["Linux", "運用保守"]


def test_tokens_azure_ops_suffix():
    assert pre_normalize_skill_tokens("Azure運用保守") == ["Azure", "運用保守"]


def test_tokens_no_suffix_single():
    """通常スキルは1トークン。"""
    assert pre_normalize_skill_tokens("Python") == ["Python"]


def test_tokens_simple_java():
    assert pre_normalize_skill_tokens("Java") == ["Java"]


def test_tokens_exp_suffix_lookup_hit():
    """lookup が解決できれば経験末尾をstrip。"""
    def _lookup(s: str) -> str | None:
        return "Linux" if s == "Linux" else None

    result = pre_normalize_skill_tokens("Linux経験", lookup=_lookup)
    assert result == ["Linux"]


def test_tokens_exp_suffix_lookup_miss():
    """lookup が None を返す場合は strip しない。"""
    def _lookup(s: str) -> str | None:
        return None

    result = pre_normalize_skill_tokens("Unknown開発経験", lookup=_lookup)
    assert result == ["Unknown開発経験"]


def test_tokens_exp_suffix_no_lookup():
    """lookup なしは経験strip不可（1トークンそのまま）。"""
    result = pre_normalize_skill_tokens("Python経験")
    assert result == ["Python経験"]


def test_tokens_backward_compat():
    """pre_normalize_skill_text は str 返却のまま（後方互換）。"""
    result = pre_normalize_skill_text("Azure運用保守")
    assert isinstance(result, str)
    assert result == "Azure"


def test_tokens_katakana_ops():
    """カタカナ変換後に運用保守splitが機能する。"""
    tokens = pre_normalize_skill_tokens("リナックス運用保守")
    assert tokens == ["Linux", "運用保守"]
