# -*- coding: utf-8 -*-
"""mail_pipeline.py (v5.1) が参照/更新するNotionプロパティ名を抽出して
現状の案件DB・エンジニアDBのスキーマと突合する。
"""

import json
import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
env_path = BASE / "config" / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip().strip('"')

NOTION_KEY = os.environ.get("NOTION_API_KEY", "") or os.environ.get("NOTION_TOKEN", "")

# v5.1 (現状) と 6/16版(bak_emergency) の両方を解析
targets = {
    "v5.1_current": BASE / "mail_pipeline" / "mail_pipeline.py",
    "v6.16_bak_emergency": BASE / "mail_pipeline" / "mail_pipeline.py.bak_emergency_20260617_182923",
}

# Notionプロパティのパターン: "プロパティ名": { ... type: ... }
prop_pattern = re.compile(
    r'"([^"]{1,40})"\s*:\s*\{\s*"(rich_text|title|number|select|multi_select|date|status|email|phone_number|url|checkbox|files|people|relation|formula)"'
)

# データベースIDの参照
db_id_pattern = re.compile(r'(?:database_id|DB_ID|ENGINEER_DB|PROJECT_DB)\s*[=:]\s*"([0-9a-f-]{32,40})"', re.IGNORECASE)

results = {}
for name, path in targets.items():
    if not path.exists():
        results[name] = {"error": "FILE NOT FOUND"}
        continue
    text = path.read_text(encoding="utf-8", errors="replace")
    props = sorted(set(prop_pattern.findall(text)))
    db_ids = sorted(set(db_id_pattern.findall(text)))
    results[name] = {
        "size_bytes": path.stat().st_size,
        "props_with_type": props,
        "db_ids_referenced": db_ids,
    }

print("=" * 80)
print("mail_pipeline.py プロパティ参照解析")
print("=" * 80)
for name, info in results.items():
    print(f"\n## {name}")
    if "error" in info:
        print(f"  ERROR: {info['error']}")
        continue
    print(f"  size: {info['size_bytes']} bytes")
    print(f"  DB IDs: {info['db_ids_referenced']}")
    print("  Properties (name, type):")
    for prop, typ in info["props_with_type"]:
        print(f"    - {prop!r:40s} : {typ}")

# 差分
if "v5.1_current" in results and "v6.16_bak_emergency" in results:
    if "props_with_type" in results["v5.1_current"] and "props_with_type" in results["v6.16_bak_emergency"]:
        v51 = set(results["v5.1_current"]["props_with_type"])
        v616 = set(results["v6.16_bak_emergency"]["props_with_type"])
        print("\n## 差分: v5.1(現状) vs v6.16(bak_emergency)")
        only_v51 = v51 - v616
        only_v616 = v616 - v51
        print(f"  v5.1のみ ({len(only_v51)}件): {sorted(only_v51)}")
        print(f"  v6.16のみ ({len(only_v616)}件): {sorted(only_v616)}")

# Notion 現状スキーマ取得
print("\n" + "=" * 80)
print("現状Notion DBスキーマ取得")
print("=" * 80)

if not NOTION_KEY:
    print("NOTION_API_KEY が見つかりません")
    sys.exit(0)

import urllib.request


def get_db_schema(db_id):
    url = f"https://api.notion.com/v1/databases/{db_id}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {NOTION_KEY}",
            "Notion-Version": "2022-06-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}


dbs = {
    "engineer_db": "343450ff-37c0-819d-8769-fb0a8a4ceeb1",
    "project_db": "343450ff-37c0-81e4-934e-f25f90284a3c",
}

notion_props = {}
for name, db_id in dbs.items():
    schema = get_db_schema(db_id)
    if "error" in schema:
        print(f"\n## {name} ({db_id})")
        print(f"  ERROR: {schema['error']}")
        continue
    props = schema.get("properties", {})
    print(f"\n## {name} ({db_id})")
    print(f"  Title: {schema.get('title', [{}])[0].get('plain_text', '?') if schema.get('title') else '?'}")
    print(f"  Property count: {len(props)}")
    db_props = []
    for pname, pdef in sorted(props.items()):
        db_props.append((pname, pdef.get("type", "?")))
        print(f"    - {pname!r:40s} : {pdef.get('type', '?')}")
    notion_props[name] = set(db_props)

# v5.1 が参照するプロパティ名のみで突合
print("\n" + "=" * 80)
print("v5.1が参照するプロパティ名 vs 現状Notion DBスキーマ")
print("=" * 80)

if "v5.1_current" in results and notion_props:
    v51_props_only = set(p for p, _ in results["v5.1_current"]["props_with_type"])

    all_notion_prop_names = set()
    for name, props_set in notion_props.items():
        all_notion_prop_names |= set(p for p, _ in props_set)

    missing_in_notion = v51_props_only - all_notion_prop_names
    print(f"\nv5.1が参照しているがNotionに存在しないプロパティ ({len(missing_in_notion)}件):")
    for p in sorted(missing_in_notion):
        # 機械的に false positive を弾く: 短すぎる, 英大文字のみ, 数字のみ
        if len(p) <= 2:
            continue
        print(f"  ⚠ {p!r}")
