# -*- coding: utf-8 -*-
"""Round 3 inline尚可パターン抽出テスト。"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from mail_pipeline.skill_extractor import extract_skills


def test_inline_slash_pattern():
    body = "必須: Java, Spring / 尚可: AWS, Docker"
    result = extract_skills("", body)
    assert any("java" in s.lower() for s in result["required"])
    assert any("aws" in s.lower() for s in result["optional"])
    assert any("docker" in s.lower() for s in result["optional"])


def test_inline_aoreba_pattern():
    body = "あれば尚良し：Kubernetes経験"
    result = extract_skills("", body)
    assert any("kubernetes" in s.lower() for s in result["optional"])


def test_inline_kangei_pattern():
    body = "歓迎スキル：React, TypeScript"
    result = extract_skills("", body)
    assert any("react" in s.lower() for s in result["optional"])
    assert any("typescript" in s.lower() for s in result["optional"])


def test_llm_fallback_only_when_hint_present():
    from unittest.mock import patch
    import mail_pipeline.skill_extractor as se

    with patch.object(se, "_llm_extract_optional", return_value=["Terraform"]) as mock_llm:
        se.load_skill_aliases.cache_clear()
        body = "ご提案ください。尚可のスキルは別途相談。"
        result = se.extract_skills("", body)
        mock_llm.assert_called_once()
