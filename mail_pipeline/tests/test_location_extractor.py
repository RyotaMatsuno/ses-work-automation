# -*- coding: utf-8 -*-
"""Phase 3: extract_location 勤務地抽出テスト。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from mail_pipeline.location_extractor import extract_location


def test_standard():
    assert extract_location("勤務地: 東京都港区") == "東京都港区"


def test_bracket():
    assert extract_location("【勤務地】新宿") == "新宿"


def test_remote():
    assert extract_location("フルリモート案件") == "リモート"


def test_with_parens():
    assert extract_location("勤務地: 品川（リモート併用）") == "品川"


def test_none():
    assert extract_location("Javaの案件です") is None


def test_telework_keyword():
    assert extract_location("テレワーク可能な案件です") == "リモート"


def test_multiline_body():
    body = "案件概要\n勤務地：渋谷区\n必須スキル: Python"
    assert extract_location(body) == "渋谷区"


def test_area_keyword():
    assert extract_location("エリア: 大阪市") == "大阪市"
