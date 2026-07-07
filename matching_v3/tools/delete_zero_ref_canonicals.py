"""delete_zero_ref_canonicals.py — 参照0の38件canonicalをskill_aliases.jsonから削除。

承認済み対象: 松野承認済み（2026-07-06 canonical_audit dry-run 結果に基づく）
承認スコープ: aliases / soft_aliases 含む全エイリアス削除が承認範囲（2026-07-06）
承認エビデンス: matching_v3/tools/output/canonical_audit_report.md（参照0リスト）
LLM不使用（ルールベースのみ）。

実行方法:
  python delete_zero_ref_canonicals.py            # dry-run（デフォルト、ファイル変更なし）
  python delete_zero_ref_canonicals.py --execute  # 本番実行
  python delete_zero_ref_canonicals.py --execute --force-skip-audit  # 監査レポート照合スキップ

注意: --execute 実行時はインタラクティブ確認なしで即時書き換えが行われる。
これは auto_runner/jobz 経由の自動実行がハングするため意図的な設計である。
誤実行防止は --execute フラグの明示指定に委ねる。
"""

from __future__ import annotations

import argparse
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
AUDIT_REPORT_PATH = Path(__file__).resolve().parent / "output" / "canonical_audit_report.md"
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


_AUDIT_HEADER_WORDS = frozenset(["canonical", "合計", "人材参照", "案件参照", "エイリアス数"])


def _parse_zero_ref_from_audit(report_path: Path) -> frozenset[str]:
    """canonical_audit_report.md から合計参照数=0のcanonicalセットを抽出する。

    テーブル形式:
        | canonical | 判定理由 | 人材参照 | 案件参照 | 合計 | 削除影響見立て | エイリアス数 |
    合計カラム（インデックス5）が "0" の行のみを対象とする。
    ヘッダー行・セパレーター行は numeric チェック + キーワードチェックで除外する。
    """
    zero_refs: set[str] = set()
    for line in report_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        parts = [p.strip() for p in line.split("|")]
        # 形式: ['', canonical, reason, 人材参照, 案件参照, 合計, 削除影響, エイリアス数, '']
        if len(parts) < 7:
            continue
        canonical = parts[1]
        total_str = parts[5]
        # ヘッダー行（「canonical」「合計」等を含む）とセパレーター行を除外
        if canonical in _AUDIT_HEADER_WORDS or total_str in _AUDIT_HEADER_WORDS:
            continue
        if set(canonical) <= set("-"):  # セパレーター行 (----)
            continue
        try:
            total = int(total_str)
        except ValueError:
            continue
        if total == 0 and canonical:
            zero_refs.add(canonical)
    return frozenset(zero_refs)


def _check_audit_report(report_path: Path) -> None:
    """TARGET_CANONICALSと監査レポートの参照0リストが一致することを確認する。"""
    if not report_path.exists():
        raise FileNotFoundError(
            f"[ERROR] 監査レポートが見つかりません: {report_path}\n"
            "  --force-skip-audit で回避可"
        )
    audit_zeros = _parse_zero_ref_from_audit(report_path)
    if audit_zeros != TARGET_CANONICALS:
        only_in_target = TARGET_CANONICALS - audit_zeros
        only_in_audit = audit_zeros - TARGET_CANONICALS
        lines = ["[ERROR] TARGET_CANONICALSと監査レポート参照0リストが一致しません。"]
        if only_in_target:
            lines.append(f"  TARGET_CANONICALSのみ（監査レポートにない）: {sorted(only_in_target)}")
        if only_in_audit:
            lines.append(f"  監査レポートのみ（TARGET_CANONICALSにない）: {sorted(only_in_audit)}")
        lines.append("  --force-skip-audit で回避可")
        raise ValueError("\n".join(lines))


def run_delete(
    aliases_path: Path = ALIASES_PATH,
    engineers_path: Path = ENGINEERS_PATH,
    structured_path: Path = STRUCTURED_PATH,
    audit_report_path: Path = AUDIT_REPORT_PATH,
    dry_run: bool = True,
    force_skip_audit: bool = False,
) -> dict:
    """削除処理を実行し、結果dictを返す。

    戻り値:
        {
            "deleted": [canonical, ...],
            "skipped_with_reason": [{"canonical": ..., "reason": ...}, ...],
            "counts_before_after": {"before": int, "after": int},
            "aliases_removed": int,
            "soft_aliases_removed": int,
            "force_skip_audit_used": bool,
        }
    """
    aliases_data = json.loads(aliases_path.read_text(encoding="utf-8"))
    canonical_list_before: list[str] = list(aliases_data.get("canonical_skills", []))
    count_before = len(canonical_list_before)

    # normalizerインポートと参照データ読み込みをバックアップ前に確認する
    # （ImportError / FileNotFoundError 時にバックアップだけ残る状態を防ぐ）
    normalizer = _load_normalizer(aliases_path)
    tokens = _collect_tokens(engineers_path, structured_path)

    # 監査レポートとの照合（バックアップ前）
    if not force_skip_audit:
        _check_audit_report(audit_report_path)

    # バックアップ（dry_run時はスキップ。時刻付与で同日2回実行による上書き消失を防止）
    if not dry_run:
        ts = datetime.now(JST).strftime("%Y%m%d_%H%M%S")
        bak_path = aliases_path.with_name(f"skill_aliases.json.bak_canonical38_{ts}")
        bak_path.write_text(aliases_path.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"[INFO] バックアップ作成: {bak_path.name}")

    # 参照カウント再検証
    alias_index = _build_alias_index(aliases_data)

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
            "soft_aliases_removed": 0,
            "force_skip_audit_used": force_skip_audit,
        }

    # canonical_skills から削除対象を除外
    deleted_set = set(deleted)
    new_canonicals = [c for c in canonical_list_before if c not in deleted_set]

    # aliases から削除対象のcanonicalを持つエントリを除外
    old_aliases: dict[str, str] = aliases_data.get("aliases", {})
    new_aliases = {k: v for k, v in old_aliases.items() if v not in deleted_set}
    aliases_removed = len(old_aliases) - len(new_aliases)

    # soft_aliases も同様に除外（承認スコープ：松野承認済み 2026-07-06）
    old_soft: dict[str, str] = aliases_data.get("soft_aliases", {})
    new_soft = {k: v for k, v in old_soft.items() if v not in deleted_set}

    count_after = len(new_canonicals)

    soft_aliases_removed = len(old_soft) - len(new_soft)

    if not dry_run:
        if force_skip_audit:
            print("[WARNING] --force-skip-audit が使用されました（監査レポート照合スキップ）—ログに記録します")
        aliases_data["canonical_skills"] = new_canonicals
        aliases_data["aliases"] = new_aliases
        aliases_data["soft_aliases"] = new_soft
        aliases_path.write_text(
            json.dumps(aliases_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"[INFO] skill_aliases.json 更新: {count_before} → {count_after} canonicals")
        print(f"[INFO] aliases 削除: {aliases_removed}件, soft_aliases 削除: {soft_aliases_removed}件")

    # 検証
    _validate(new_canonicals, new_aliases, new_soft, count_before, count_after, len(deleted))

    result = {
        "deleted": deleted,
        "skipped_with_reason": skipped,
        "counts_before_after": {"before": count_before, "after": count_after},
        "aliases_removed": aliases_removed,
        "soft_aliases_removed": soft_aliases_removed,
        "force_skip_audit_used": force_skip_audit,
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
    """削除後の整合性検証。python -O でも無効化されないよう assert でなく ValueError を使う。"""
    expected_after = count_before - deleted_count
    if count_after != expected_after:
        raise ValueError(
            f"canonical件数不整合: expected {expected_after}, got {count_after}"
        )

    canonical_set = set(new_canonicals)
    dangling = {k: v for k, v in new_aliases.items() if v not in canonical_set}
    dangling.update({k: v for k, v in new_soft.items() if v not in canonical_set})
    if dangling:
        raise ValueError(
            f"dangling alias が {len(dangling)}件残存: {list(dangling.items())[:5]}"
        )

    print(f"[OK] 検証完了: canonical {count_before} → {count_after}, dangling=0")


def _write_log(result: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(JST).strftime("%Y%m%d_%H%M%S")
    log_path = OUTPUT_DIR / f"canonical38_delete_log_{ts}.json"
    log_data = {
        "generated": datetime.now(JST).isoformat(),
        **result,
    }
    log_path.write_text(json.dumps(log_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[INFO] ログ出力: {log_path.name}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "参照0の38件canonicalをskill_aliases.jsonから削除する。"
            "デフォルトはdry-run（ファイル変更なし）。"
        )
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="実際に skill_aliases.json を書き換える（指定なしはdry-runのみ）",
    )
    parser.add_argument(
        "--force-skip-audit",
        action="store_true",
        help="canonical_audit_report.md との照合をスキップして実行する",
    )
    args = parser.parse_args()

    dry_run = not args.execute
    if dry_run:
        print("[INFO] dry-run モード（--execute なし）: ファイルは変更されません")

    result = run_delete(dry_run=dry_run, force_skip_audit=args.force_skip_audit)

    print(f"\n--- 結果サマリ ---")
    print(f"削除: {len(result['deleted'])}件")
    print(f"スキップ: {len(result['skipped_with_reason'])}件")
    before = result["counts_before_after"]["before"]
    after = result["counts_before_after"]["after"]
    print(f"canonical件数: {before} → {after}")
    print(f"aliases削除: {result['aliases_removed']}件")
    print(f"soft_aliases削除: {result['soft_aliases_removed']}件")
    if result["force_skip_audit_used"]:
        print("[WARNING] --force-skip-audit が使用されました")


if __name__ == "__main__":
    main()
