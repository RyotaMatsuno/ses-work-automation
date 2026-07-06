"""スキル正規化バッチスクリプト。
全エンジニアの「スキル」を skill_aliases.json で正規化し「正規化スキル」に書き込む。

Usage:
    python scripts/normalize_all_skills.py --dry-run
    python scripts/normalize_all_skills.py --apply
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config import Config
from matcher import SkillNormalizer, canonicalize_skill_list
from notion_client import NotionClient

JST = timezone(timedelta(hours=9))
_ALIASES_PATH = _ROOT / "skill_aliases.json"


def normalize_engineer_skills(
    engineer: dict[str, Any],
    normalizer: SkillNormalizer,
) -> list[str]:
    """エンジニアのスキルを正規化して返す。スキルなしなら空リスト。"""
    raw = [str(s) for s in (engineer.get("スキル") or [])]
    if not raw:
        return []
    return canonicalize_skill_list(raw, normalizer)


def _build_report(
    engineers: list[dict[str, Any]],
    normalizer: SkillNormalizer,
    *,
    sample_size: int = 10,
) -> dict[str, Any]:
    before_all: list[str] = []
    after_all: list[str] = []
    resolved_count = 0
    total_count = 0
    skip_count = 0
    samples: list[dict] = []
    unresolved_skills: list[str] = []

    for eng in engineers:
        raw = [str(s) for s in (eng.get("スキル") or [])]
        if not raw:
            skip_count += 1
            continue
        normalized = canonicalize_skill_list(raw, normalizer)
        before_all.extend(raw)
        after_all.extend(normalized)
        for skill in raw:
            total_count += 1
            if normalizer.resolve_canonical(skill) is not None:
                resolved_count += 1
            else:
                unresolved_skills.append(skill)
        if len(samples) < sample_size:
            samples.append({"名前": eng.get("名前", ""), "before": raw, "after": normalized})

    return {
        "total_engineers": len(engineers),
        "skip_count": skip_count,
        "unique_before": len(set(before_all)),
        "unique_after": len(set(after_all)),
        "total_skills": total_count,
        "resolved_count": resolved_count,
        "resolution_rate": resolved_count / total_count if total_count > 0 else 0.0,
        "unresolved_top": Counter(unresolved_skills).most_common(20),
        "samples": samples,
    }


def _write_report(report: dict[str, Any], *, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# スキル正規化レポート",
        f"生成: {now}",
        "",
        f"エンジニア総数: {report['total_engineers']}",
        f"スキルなし（スキップ）: {report['skip_count']}",
        f"ユニークスキル数 before: {report['unique_before']}",
        f"ユニークスキル数 after:  {report['unique_after']}",
        f"解決率: {report['resolution_rate']:.1%} ({report['resolved_count']}/{report['total_skills']})",
        "",
        "## 未解決スキル Top 20",
    ]
    for skill, count in report["unresolved_top"]:
        lines.append(f"- {skill} ({count}件)")
    lines += ["", f"## サンプル {len(report['samples'])} 名"]
    for s in report["samples"]:
        lines += [f"\n### {s['名前']}", f"- before: {s['before']}", f"- after:  {s['after']}"]

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"レポート出力: {output_path}")


def run(*, dry_run: bool) -> None:
    cfg = Config()
    client = NotionClient(config=cfg)
    normalizer = SkillNormalizer(_ALIASES_PATH)

    if not dry_run:
        print("正規化スキルプロパティの存在確認・追加中...")
        if not client.ensure_normalized_skill_property():
            print("[ERROR] 正規化スキルプロパティの追加に失敗しました。処理を中止します。")
            return

    print("エンジニア全件取得中...")
    engineers = client.get_all_engineers()
    print(f"取得件数: {len(engineers)}")

    report = _build_report(engineers, normalizer)
    print(
        f"解決率: {report['resolution_rate']:.1%} "
        f"({report['resolved_count']}/{report['total_skills']})"
    )
    print(f"スキップ（スキルなし）: {report['skip_count']} 件")

    report_path = _ROOT / "research_results" / "skill_normalize_report.md"
    _write_report(report, output_path=report_path)

    if dry_run:
        print("[DRY-RUN] Notion 更新はスキップ")
        return

    success = 0
    failed = 0
    for eng in engineers:
        normalized = normalize_engineer_skills(eng, normalizer)
        if not normalized:
            continue
        existing = eng.get("正規化スキル") or []
        if existing == normalized:
            continue
        ok = client.update_engineer_normalized_skills(eng["id"], normalized)
        if ok:
            success += 1
        else:
            failed += 1
            print(f"[WARN] 更新失敗: {eng.get('名前', eng['id'])}")
    print(f"完了: 成功={success} 失敗={failed}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="スキル正規化バッチ")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", dest="dry_run")
    group.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    run(dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
