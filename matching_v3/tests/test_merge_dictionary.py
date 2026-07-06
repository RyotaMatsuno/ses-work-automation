# -*- coding: utf-8 -*-
"""merge_dictionary スクリプトのテスト。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

MATCHING_V3 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MATCHING_V3))

from merge_dictionary import MANUAL_ALIASES, run


def test_manual_aliases_include_c_and_ut():
    assert MANUAL_ALIASES["c言語"] == "C"
    assert MANUAL_ALIASES["ut"] == "単体テスト"


def test_merge_dry_run_no_write(tmp_path, monkeypatch):
    aliases_path = tmp_path / "skill_aliases.json"
    aliases_path.write_text(
        json.dumps({"canonical_skills": ["Java"], "aliases": {"java": "Java"}}, ensure_ascii=False),
        encoding="utf-8",
    )
    results_dir = tmp_path / "research_results"
    results_dir.mkdir()
    candidates = results_dir / "skill_add_candidates_20260625.json"
    candidates.write_text(
        json.dumps(
            [
                {
                    "skill": "Firewall",
                    "class": "tech_skill",
                    "canonical_form": "Firewall",
                    "confidence": 0.99,
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    import merge_dictionary as md

    monkeypatch.setattr(md, "ALIASES_PATH", aliases_path)
    monkeypatch.setattr(md, "RESULTS_DIR", results_dir)

    report = run(execute=False)
    assert report["stats"]["auto_merged"] == 1
    data = json.loads(aliases_path.read_text(encoding="utf-8"))
    assert data["aliases"] == {"java": "Java"}
