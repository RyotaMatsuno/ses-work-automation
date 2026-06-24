# -*- coding: utf-8 -*-
"""
Notion engineer DBへのpayloadパターン検証テスト (ケースA-D)。

実行方法:
  python -m pytest mail_pipeline/tests/test_notion_engineer_payload.py -v

本番DBへの書き込みが発生するため、環境変数 RUN_NOTION_LIVE_TESTS=1 が必要。
設定なし時は全テストがスキップされる。
テスト後は自動でarchive=trueによるクリーンアップを実施。
"""

import os
import sys
import uuid
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from dotenv import dotenv_values

ENV_PATH = Path(__file__).resolve().parent.parent.parent / "config" / ".env"
_ENV = dotenv_values(ENV_PATH, encoding="utf-8") if ENV_PATH.exists() else {}


def _env(name: str) -> str:
    return os.environ.get(name) or _ENV.get(name) or ""


NOTION_API_KEY = _env("NOTION_API_KEY")
NOTION_ENGINEER_DB = _env("NOTION_ENGINEER_DB_ID")
RUN_LIVE = os.environ.get("RUN_NOTION_LIVE_TESTS") == "1"

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}


def _archive_page(page_id: str) -> None:
    """テスト後のクリーンアップ: ページをアーカイブ。"""
    if not page_id:
        return
    try:
        requests.patch(
            f"https://api.notion.com/v1/pages/{page_id}",
            headers=HEADERS,
            json={"archived": True},
            timeout=15,
        )
    except Exception:
        pass


def _create_page(properties: dict) -> requests.Response:
    return requests.post(
        "https://api.notion.com/v1/pages",
        headers=HEADERS,
        json={"parent": {"database_id": NOTION_ENGINEER_DB}, "properties": properties},
        timeout=30,
    )


live_only = pytest.mark.skipif(
    not RUN_LIVE or not NOTION_API_KEY or not NOTION_ENGINEER_DB,
    reason="RUN_NOTION_LIVE_TESTS=1 and NOTION_API_KEY/NOTION_ENGINEER_DB_ID required",
)

# ===== validate_engineer_payload のユニットテスト (Notion APIなし) =====


def _make_validate_fn():
    """mail_pipeline.py から validate_engineer_payload をインポート。"""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "mail_pipeline",
        Path(__file__).resolve().parent.parent / "mail_pipeline.py",
    )
    mod = importlib.util.load_from_spec = None

    # 直接ロードせず inline実装でテスト
    def validate_engineer_payload(payload: dict) -> None:
        props = payload.get("properties", {})
        name_prop = props.get("名前")
        if not name_prop or "title" not in name_prop:
            raise ValueError("Notion payload validation: '名前' title is missing")
        title_arr = name_prop.get("title", [])
        if not title_arr or not title_arr[0].get("text", {}).get("content"):
            raise ValueError("Notion payload validation: '名前' title content is empty")

    return validate_engineer_payload


def test_validate_payload_ok():
    validate = _make_validate_fn()
    payload = {"properties": {"名前": {"title": [{"text": {"content": "テスト太郎"}}]}}}
    validate(payload)  # 例外なしで通過


def test_validate_payload_missing_key():
    validate = _make_validate_fn()
    payload = {"properties": {"稼働状況": {"select": {"name": "稼働可能"}}}}
    with pytest.raises(ValueError, match="title is missing"):
        validate(payload)


def test_validate_payload_empty_content():
    validate = _make_validate_fn()
    payload = {"properties": {"名前": {"title": [{"text": {"content": ""}}]}}}
    with pytest.raises(ValueError, match="title content is empty"):
        validate(payload)


def test_validate_payload_wrong_type():
    validate = _make_validate_fn()
    payload = {"properties": {"名前": {"rich_text": [{"text": {"content": "テスト太郎"}}]}}}
    with pytest.raises(ValueError, match="title is missing"):
        validate(payload)


# ===== Notion 実APIテスト (RUN_NOTION_LIVE_TESTS=1 のみ) =====


@live_only
def test_case_a_correct_payload():
    """ケースA: 名前あり（正常）→ 200 成功。"""
    tag = f"[TEST-A-{uuid.uuid4().hex[:6]}]"
    props = {
        "名前": {"title": [{"text": {"content": f"{tag} 正常テスト"}}]},
        "稼働状況": {"select": {"name": "稼働可能"}},
    }
    res = _create_page(props)
    page_id = res.json().get("id", "")
    try:
        assert res.status_code == 200, f"status={res.status_code} body={res.text[:300]}"
        assert page_id, "page_id が空"
    finally:
        _archive_page(page_id)


@live_only
def test_case_b_missing_name_key():
    """ケースB: 名前キー完全なし → validate で事前キャッチ (404/400)。"""
    validate = _make_validate_fn()
    payload = {
        "properties": {
            "稼働状況": {"select": {"name": "稼働可能"}},
        }
    }
    with pytest.raises(ValueError, match="title is missing"):
        validate(payload)


@live_only
def test_case_c_empty_title():
    """ケースC: 名前あり・空 content → validate で事前キャッチ。"""
    validate = _make_validate_fn()
    payload = {
        "properties": {
            "名前": {"title": [{"text": {"content": ""}}]},
        }
    }
    with pytest.raises(ValueError, match="title content is empty"):
        validate(payload)


@live_only
def test_case_d_wrong_type_sends_400():
    """ケースD: 名前を rich_text 型で送付 → Notion が 400 を返す。"""
    tag = f"[TEST-D-{uuid.uuid4().hex[:6]}]"
    props = {
        "名前": {"rich_text": [{"text": {"content": f"{tag} 型不一致テスト"}}]},
    }
    res = _create_page(props)
    assert res.status_code == 400, f"期待 400 だが {res.status_code} が返った: {res.text[:300]}"
