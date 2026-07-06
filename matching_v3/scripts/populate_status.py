"""稼働状況 populate バッチスクリプト。
メモ（備考LINEメモ）のキーワード分析で稼働状況を判定し、Notion DBに投入する。

Usage:
    python scripts/populate_status.py --dry-run
    python scripts/populate_status.py --apply
"""
from __future__ import annotations

import argparse
import sys
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
from notion_client import NotionClient

JST = timezone(timedelta(hours=9))

# 優先度順（上位カテゴリが先にマッチする）
_ADJUSTING_KEYWORDS = ["辞退", "休養", "引退", "対象外", "提案不可", "営業停止"]
_WORKING_KEYWORDS = ["稼働中", "参画中", "就業中", "常駐中", "現在稼働", "現場"]
_AVAILABLE_KEYWORDS = ["稼働可能", "即日稼働", "即稼働", "即日", "参画可能", "フリー", "空き", "待機中", "案件探し"]


def detect_status(memo: str) -> str | None:
    """メモから稼働状況を推定する。判定できなければ None。"""
    if not memo:
        return None
    for kw in _ADJUSTING_KEYWORDS:
        if kw in memo:
            return "調整中"
    for kw in _WORKING_KEYWORDS:
        if kw in memo:
            return "稼働中"
    for kw in _AVAILABLE_KEYWORDS:
        if kw in memo:
            return "稼働可能"
    return None


def classify_engineers(engineers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """未設定エンジニアのうち稼働状況を設定すべき対象を返す。"""
    targets: list[dict[str, Any]] = []
    for eng in engineers:
        if eng.get("稼働状況"):
            continue
        memo = eng.get("備考（LINEメモ）") or ""
        detected = detect_status(memo)
        if detected is None:
            continue
        targets.append({
            "id": eng["id"],
            "名前": eng.get("名前", ""),
            "memo_excerpt": memo[:80],
            "detected_status": detected,
        })
    return targets


def _write_report(
    targets: list[dict[str, Any]],
    total: int,
    *,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")
    by_status: dict[str, list] = {}
    for t in targets:
        by_status.setdefault(t["detected_status"], []).append(t)

    lines = [
        "# 稼働状況 populate レポート",
        f"生成: {now}",
        "",
        f"エンジニア総数: {total}",
        f"設定対象（空欄→有値）: {len(targets)} 件",
        "",
        "## 内訳",
    ]
    for status, items in sorted(by_status.items()):
        lines.append(f"\n### {status}（{len(items)} 件）")
        for item in items[:20]:
            lines.append(f"- {item['名前']} — `{item['memo_excerpt']}`")
        if len(items) > 20:
            lines.append(f"  ... 他 {len(items) - 20} 件")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"レポート出力: {output_path}")


def run(*, dry_run: bool) -> None:
    cfg = Config()
    client = NotionClient(config=cfg)
    print("エンジニア全件取得中...")
    engineers = client.get_all_engineers()
    print(f"取得件数: {len(engineers)}")

    targets = classify_engineers(engineers)
    print(f"稼働状況設定対象: {len(targets)} 件")

    report_path = _ROOT / "research_results" / "status_populate_report.md"
    _write_report(targets, len(engineers), output_path=report_path)

    if dry_run:
        print("[DRY-RUN] Notion 更新はスキップ")
        for t in targets:
            print(f"  {t['名前']} → {t['detected_status']}")
        return

    success = 0
    failed = 0
    for t in targets:
        ok = client.update_engineer_status(t["id"], t["detected_status"])
        if ok:
            success += 1
        else:
            failed += 1
            print(f"[WARN] 更新失敗: {t['名前']} ({t['id']})")
    print(f"完了: 成功={success} 失敗={failed}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="稼働状況 populate バッチ")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", dest="dry_run")
    group.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    run(dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
