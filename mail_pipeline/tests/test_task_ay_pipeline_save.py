# -*- coding: utf-8 -*-
"""Task AY: mail_pipeline Notion保存・バックフィル・バリデーション。"""

from __future__ import annotations

import sys
from pathlib import Path

SES_WORK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SES_WORK))

from mail_pipeline.project_notion_save import (
    BACKFILL_SOURCE_TAG,
    backfill_note_append,
    canonicalize_skills_for_notion,
    extract_skills_for_backfill,
    log_project_save_warnings,
    prepare_notion_project_fields,
    subject_has_skill_hint,
)


def test_canonicalize_java_variants():
    skills = canonicalize_skills_for_notion(["java", "JAVA", "Java/Spring"])
    assert "Java" in skills
    assert "Spring" in skills


def test_prepare_notion_project_fields_from_body():
    info = {"type": "project", "name": "Java案件"}
    subject = "Java/Spring 業務システム"
    body = "必須: Java, Spring\n単価: 70万\n勤務地: 東京"
    req, opt, price, location = prepare_notion_project_fields(info, subject, body)
    assert "Java" in req
    assert price == 70.0
    assert location and "東京" in location


def test_register_project_dry_run():
    msgs: list[str] = []

    def _capture(msg, *args):
        msgs.append(msg % args if args else msg)

    info = {
        "type": "project",
        "name": "React案件",
        "required_skills": ["react"],
        "price": 65,
        "location": "横浜",
    }
    req, opt, price, location = prepare_notion_project_fields(
        info,
        "React TypeScript フロント",
        "必須: React, TypeScript\n単価65万\n勤務地: 横浜",
    )
    properties = {
        "必要スキル": {"multi_select": [{"name": s} for s in req]},
        "尚可スキル": {"multi_select": [{"name": s} for s in opt]},
        "単価（万円）": {"number": price},
        "案件詳細": {"rich_text": [{"text": {"content": "detail"}}]},
    }
    log_project_save_warnings("React案件", properties, "React", "body", log_fn=_capture)
    assert req
    assert price == 65.0
    assert location and "横浜" in location


def test_register_project_payload_skills_via_internal_prepare():
    """prepare_notion_project_fields が multi_select 用スキルを返すこと。"""
    info = {"name": "Go案件"}
    req, _, price, _ = prepare_notion_project_fields(
        info,
        "Go言語 サーバ開発",
        "必須: Go\n単価: 60万",
    )
    assert req
    assert price == 60.0


def test_validation_warns_empty_skills_with_hint():
    warnings: list[str] = []
    properties = {
        "必要スキル": {"multi_select": []},
        "単価（万円）": {"number": None},
        "案件詳細": {"rich_text": []},
    }
    log_project_save_warnings(
        "Java AWS案件",
        properties,
        "Java AWS インフラ",
        "クラウド構築",
        log_fn=lambda msg, *args: warnings.append(msg % args if args else msg),
    )
    assert any("必要スキルが空" in w for w in warnings)
    assert subject_has_skill_hint("Java AWS", "本文")


def test_backfill_dry_run_extract():
    req, opt = extract_skills_for_backfill(
        "Python Django案件",
        "必須: Python, Django\n尚可: AWS",
        "",
    )
    assert "Python" in req


def test_backfill_note_tag():
    assert BACKFILL_SOURCE_TAG in backfill_note_append("")
    assert BACKFILL_SOURCE_TAG in backfill_note_append("既存メモ")


def test_prepare_notion_project_fields_bracket_location():
    info = {"type": "project", "name": "案件"}
    _, _, _, location = prepare_notion_project_fields(
        info,
        "案件",
        "【勤務地】新宿\n必須: Java",
    )
    assert location == "新宿"


def test_prepare_notion_project_fields_remote_keyword():
    info = {"type": "project", "name": "案件"}
    _, _, _, location = prepare_notion_project_fields(
        info,
        "フルリモート案件",
        "必須: Python",
    )
    assert location == "リモート"


def test_prepare_notion_project_fields_preserves_existing_location():
    info = {"type": "project", "name": "案件", "location": "大阪"}
    _, _, _, location = prepare_notion_project_fields(
        info,
        "案件",
        "【勤務地】新宿",
    )
    assert location == "大阪"


def test_backfill_script_dry_run(monkeypatch):
    import scripts.backfill_case_skills as mod

    fake_page = {
        "id": "page-1",
        "properties": {
            "案件名": {"title": [{"plain_text": "Java案件"}]},
            "案件詳細": {"rich_text": [{"plain_text": "必須: Java, Spring"}]},
            "案件情報原文": {"rich_text": []},
            "必要スキル": {"multi_select": []},
            "尚可スキル": {"multi_select": []},
        },
    }
    monkeypatch.setattr(mod, "PROJECT_DB", "db-id")
    monkeypatch.setattr(mod, "query_empty_skill_cases", lambda limit: [fake_page])
    monkeypatch.setattr(mod, "get_database_property_names", lambda _db: {"備考"})
    stats = mod.run_backfill(dry_run=True, limit=1)
    assert stats["patched"] == 1
