"""delete_zero_ref_canonicals.py — 参照0の38件canonicalをskill_aliases.jsonから削除。

承認済み対象: 松野承認済み（2026-07-06 canonical_audit dry-run 結果に基づく）
LLM不使用（ルールベースのみ）。
"""

from __future__ import annotations

import json
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parents[1]
SES_WORK = BASE_DIR.parent
ALIASES_PATH = BASE_DIR / "skill_aliases.json"
ENGINEERS_PATH = SES_WORK / "poc_engineers.json"
STRUCTURED_PATH = BASE_DIR / "logs" / "structured.jsonl"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"

JST = timezone(timedelta(hours=9))

# 承認済み削除対象38件（canonical_audit_report.md 2026-07-06 参照0リストと完全一致）
TARGET_CANONICALS: frozenset[str] = frozenset([
    "Ad-hoc",
    "BusinessUser",
    "Company",
    "Construction Industry Experience",
    "Construction Site Experience",
    "Consumer Content Creator",
    "Customer Negotiation Experience",
    "GS21",
    "Hourly Settlement",
    "InterviewAvailability",
    "Life Insurance Operations",
    "OnSiteWork",
    "Operations Experience",
    "POSITIVE",
    "ParallelStatus",
    "ProactiveBehavior",
    "Satellite Office",
    "Self-management",
    "Senior Practitioner",
    "Shift Example",
    "Telecommunications Experience",
    "AIサービス業務",
    "DBA",
    "PL経験",
    "SRE",
    "ec系業務",
    "インフラエンジニア",
    "スタートアップ業務",
    "フィールドプランナー",
    "ログ",
    "人材採用",
    "営業部門業務",
    "採用人事",
    "採用人事業務",
    "業務推進",
    "生成AI業務",
    "金融商品取引経験",
    "金融業界業務",
])


def _norm_key(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).lower().split())


def _build_alias_index(aliases_data: dict) -> dict[str, list[str]]:
    """canonical -> [alias keys]"""
    index: dict[str, list[str]] = defaultdict(list)
    for key, canonical in aliases_data.get("aliases", {}).items():
        index[canonical].append(key)
    return dict(index)


def _collect_tokens(engineers_path: Path, structured_path: Path) -> list[tuple[str, str]]:
    tokens: list[tuple[str, str]] = []
    if structured_path.exists():
        with structured_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                for bucket in ("required_skills", "optional_skills", "ambiguous_skills"):
                    for s in row.get(bucket) or []:
                        t = str(s).strip()
                        if t:
                            tokens.append((t, "案件"))
    if engineers_path.exists():
        data = json.loads(engineers_path.read_text(encoding="utf-8"))
        for eng in data:
            raw = eng.get("skills") or eng.get("スキル") or ""
            if isinstance(raw, str):
                parts = [p.strip() for p in raw.replace("/", ",").split(",") if p.strip()]
            else:
                parts = [str(p).strip() for p in raw]
            for s in parts:
                if s:
                    tokens.append((s, "人材"))
    return tokens


def _count_refs(
    canonical: str,
    alias_keys: list[str],
    tokens: list[tuple[str, str]],
    normalizer,
) -> dict[str, int]:
    """canonical への参照カウント（canonical_audit.py と同一ロジック）。"""
    counts: Counter[str] = Counter()
    targets = {canonical.lower()}
    targets.update(k.lower() for k in alias_keys)
    targets_norm = {_norm_key(t) for t in targets}

    for raw, source in tokens:
        resolved = normalizer.resolve_canonical(raw)
        if resolved == canonical:
            counts[source] += 1
            continue
        raw_norm = _norm_key(raw)
        if raw_norm in targets_norm or raw.lower() in targets:
            counts[source] += 1
    return dict(counts)


def _load_normalizer(aliases_path: Path):
    if str(BASE_DIR) not in sys.path:
        sys.path.insert(0, str(BASE_DIR))
    from matcher import SkillNormalizer
    return SkillNormalizer(aliases_path)


def run_delete(
    aliases_path: Path = ALIASES_PATH,
    engineers_path: Path = ENGINEERS_PATH,
    structured_path: Path = STRUCTURED_PATH,
    dry_run: bool = False,
) -> dict:
    """削除処理を実行し、結果dictを返す。

    戻り値:
        {
            "deleted": [canonical, ...],
            "skipped_with_reason": [{"canonical": ..., "reason": ...}, ...],
            "counts_before_after": {"before": int, "after": int},
            "aliases_removed": int,
        }
    """
    aliases_data = json.loads(aliases_path.read_text(encoding="utf-8"))
    canonical_list_before: list[str] = list(aliases_data.get("canonical_skills", []))
    count_before = len(canonical_list_before)

    # バックアップ（dry_run時はスキップ）
    if not dry_run:
        date_str = datetime.now(JST).strftime("%Y%m%d")
        bak_path = aliases_path.with_name(f"skill_aliases.json.bak_canonical38_{date_str}")
        bak_path.write_text(aliases_path.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"[INFO] バックアップ作成: {bak_path.name}")

    # 参照カウント再検証
    alias_index = _build_alias_index(aliases_data)
    tokens = _collect_tokens(engineers_path, structured_path)
    normalizer = _load_normalizer(aliases_path)

    deleted: list[str] = []
    skipped: list[dict] = []
    canonical_set_in_file = set(canonical_list_before)

    for canonical in sorted(TARGET_CANONICALS):
        if canonical not in canonical_set_in_file:
            continue  # ファイルに存在しない場合はスキップ
        alias_keys = alias_index.get(canonical, [])
        refs = _count_refs(canonical, alias_keys, tokens, normalizer)
        total = refs.get("人材", 0) + refs.get("案件", 0)
        if total > 0:
            reason = (
                f"実行時参照あり（人材={refs.get('人材', 0)}, 案件={refs.get('案件', 0)}）— "
                "監査時との参照ズレのためスキップ"
            )
            print(f"[WARNING] SKIP {canonical!r}: {reason}")
            skipped.append({"canonical": canonical, "reason": reason})
        else:
            deleted.append(canonical)

    if not deleted:
        print("[INFO] 削除対象なし（全件スキップ）")
        return {
            "deleted": [],
            "skipped_with_reason": skipped,
            "counts_before_after": {"before": count_before, "after": count_before},
            "aliases_removed": 0,
        }

    # canonical_skills から削除対象を除外
    deleted_set = set(deleted)
    new_canonicals = [c for c in canonical_list_before if c not in deleted_set]

    # aliases から削除対象のcanonicalを持つエントリを除外
    old_aliases: dict[str, str] = aliases_data.get("aliases", {})
    new_aliases = {k: v for k, v in old_aliases.items() if v not in deleted_set}
    aliases_removed = len(old_aliases) - len(new_aliases)

    # soft_aliases も同様に除外
    old_soft: dict[str, str] = aliases_data.get("soft_aliases", {})
    new_soft = {k: v for k, v in old_soft.items() if v not in deleted_set}

    count_after = len(new_canonicals)

    if not dry_run:
        aliases_data["canonical_skills"] = new_canonicals
        aliases_data["aliases"] = new_aliases
        aliases_data["soft_aliases"] = new_soft
        aliases_path.write_text(
            json.dumps(aliases_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"[INFO] skill_aliases.json 更新: {count_before} → {count_after} canonicals")
        print(f"[INFO] aliases 削除: {aliases_removed}件")

    # 検証
    _validate(new_canonicals, new_aliases, new_soft, count_before, count_after, len(deleted))

    result = {
        "deleted": deleted,
        "skipped_with_reason": skipped,
        "counts_before_after": {"before": count_before, "after": count_after},
        "aliases_removed": aliases_removed,
    }

    if not dry_run:
        _write_log(result)

    return result


def _validate(
    new_canonicals: list[str],
    new_aliases: dict[str, str],
    new_soft: dict[str, str],
    count_before: int,
    count_after: int,
    deleted_count: int,
) -> None:
    """削除後の整合性検証。"""
    expected_after = count_before - deleted_count
    assert count_after == expected_after, (
        f"canonical件数不整合: expected {expected_after}, got {count_after}"
    )

    canonical_set = set(new_canonicals)
    dangling = {k: v for k, v in new_aliases.items() if v not in canonical_set}
    dangling.update({k: v for k, v in new_soft.items() if v not in canonical_set})
    if dangling:
        raise AssertionError(
            f"dangling alias が {len(dangling)}件残存: {list(dangling.items())[:5]}"
        )

    print(f"[OK] 検証完了: canonical {count_before} → {count_after}, dangling=0")


def _write_log(result: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(JST).strftime("%Y%m%d")
    log_path = OUTPUT_DIR / f"canonical38_delete_log_{date_str}.json"
    log_data = {
        "generated": datetime.now(JST).isoformat(),
        **result,
    }
    log_path.write_text(json.dumps(log_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[INFO] ログ出力: {log_path.name}")


def main() -> None:
    result = run_delete()
    print(f"\n--- 結果サマリ ---")
    print(f"削除: {len(result['deleted'])}件")
    print(f"スキップ: {len(result['skipped_with_reason'])}件")
    before = result["counts_before_after"]["before"]
    after = result["counts_before_after"]["after"]
    print(f"canonical件数: {before} → {after}")
    print(f"aliases削除: {result['aliases_removed']}件")


if __name__ == "__main__":
    main()
