#!/usr/bin/env python3
"""OOVレポート上位語からエイリアス拡張と新規候補分離（Phase 3）。"""
from __future__ import annotations

import csv
import json
import re
import sys
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from matcher import SkillNormalizer  # noqa: E402
from skill_gate import normalize_skill_text  # noqa: E402
from skill_pre_normalize import skill_lookup_key  # noqa: E402

OOV_REPORT = BASE_DIR / "oov_report.csv"
ALIASES_PATH = BASE_DIR / "skill_aliases.json"
NEW_SKILLS_CSV = BASE_DIR / "new_skills_candidate.csv"

# Phase1上位語・表記ゆれとして確度高いもののみ（canonical は辞書に存在すること）
CURATED_ALIASES: dict[str, str] = {
    "azure運用保守": "Azure",
    "databricks運用保守": "Databricks",
    "aws運用保守": "AWS",
    "gcp運用保守": "GCP",
    "kubernetes運用保守": "Kubernetes",
    "docker運用保守": "Docker",
    "linux運用保守": "Linux",
    "windows運用保守": "Windows",
    "oracle運用保守": "Oracle",
    "mysql運用保守": "MySQL",
    "postgresql運用保守": "PostgreSQL",
    "terraform運用保守": "Terraform",
    "ansible運用保守": "Ansible",
    "jenkins運用保守": "Jenkins",
    "java運用保守": "Java",
    "python運用保守": "Python",
    "nodejs": "Node.js",
    "node js": "Node.js",
    "node.js": "Node.js",
    "react.js": "React",
    "reactjs": "React",
    "vue.js": "Vue.js",
    "vuejs": "Vue.js",
    "typescript": "TypeScript",
    "javascript": "JavaScript",
    "springboot": "Spring Boot",
    "spring boot": "Spring Boot",
    "vb net": "VB.NET",
    "vb・net": "VB.NET",
    "c sharp": "C#",
    "c-sharp": "C#",
    "soc運用": "SOC",
    "soc 運用": "SOC",
    "セキュリティー分析": "セキュリティ",
    "セキュリティ分析": "セキュリティ",
    "tier2レベルセキュリティー対応": "セキュリティ",
    "インフラ基盤の環境構築": "インフラ",
    "インフラ基盤構築": "インフラ",
    "インフラ環境構築": "インフラ",
    "クラウド環境構築": "クラウド",
    "基盤構築": "インフラ",
    "環境構築": "インフラ",
    "データ移行": "ETL",
    "snowflake": "Snowflake",
    "salesforce業務経験3年程度": "Salesforce",
    "excel": "Excel",
    "word": "Word",
    "aws案件": "AWS",
    "java案件": "Java",
    "c#人材": "C#",
    "【java": "Java",
    "4hana 販売領域": "SAP",
    "sap s": "SAP",
    "iac": "Terraform",
    "nwエンジニア": "ネットワーク",
    "intuneでのデバイス管理": "Microsoft Intune",
    "powerbiを用いたダッシュボード": "Power BI",
    "ワード>powerbi": "Power BI",
    "推論": "ML",
    "再学習": "機械学習",
    "sfaの導入実績": "Salesforce",
    "脆弱性トリアージ": "セキュリティ",
    "脆弱性診断": "セキュリティ",
    "webデザイナーとしての実務経験": "UI/UXデザイン",
    "デザインの実務経験": "UI/UXデザイン",
    "cdk": "AWS CDK",
    "データ移行／データ整備の実務経験": "ETL",
    "コンテナ": "Docker",
}

AMBIGUOUS_PATTERNS = [
    re.compile(r"^(課題|コミュニケーション|課題解決|顧客折衝|進捗管理|管理能力|リーダー|主体性)"),
    re.compile(r"customer", re.I),
    re.compile(r"experience$", re.I),
    re.compile(r"能力$"),
    re.compile(r"^【"),
    re.compile(r"ご提案|お願い|回答|尚可|外国籍|出勤|オフィス"),
    re.compile(r"^(△|○|×|および)"),
]


def _canonical_set(data: dict) -> set[str]:
    s = set(data.get("canonical_skills", []))
    s.update(data.get("skill_tiers", {}))
    s.update(data.get("aliases", {}).values())
    return s


def _is_ambiguous(skill: str) -> bool:
    return any(pat.search(skill.strip()) for pat in AMBIGUOUS_PATTERNS)


def main() -> int:
    data = json.loads(ALIASES_PATH.read_text(encoding="utf-8"))
    canonicals = _canonical_set(data)
    normalizer = SkillNormalizer(ALIASES_PATH)

    report_rows: list[dict[str, str]] = []
    if OOV_REPORT.exists():
        with OOV_REPORT.open(encoding="utf-8", newline="") as f:
            report_rows = list(csv.DictReader(f))

    new_aliases: dict[str, str] = {}
    candidates: list[dict[str, str]] = []

    # レポート上位100から curated / candidate を分類
    for row in report_rows[:100]:
        skill = row.get("skill", "").strip()
        if not skill:
            continue
        key = skill_lookup_key(skill)
        if key in CURATED_ALIASES and CURATED_ALIASES[key] in canonicals:
            if key not in data["aliases"]:
                new_aliases[key] = CURATED_ALIASES[key]
            continue
        if normalizer.resolve_canonical(normalize_skill_text(skill)):
            continue
        if _is_ambiguous(skill):
            candidates.append(
                {
                    "skill": skill,
                    "count": row.get("count", ""),
                    "source": row.get("source", ""),
                    "reason": "曖昧語/非技術の可能性",
                    "suggested_canonical": "",
                }
            )
        else:
            candidates.append(
                {
                    "skill": skill,
                    "count": row.get("count", ""),
                    "source": row.get("source", ""),
                    "reason": "親canonical不明（要松野確認）",
                    "suggested_canonical": "",
                }
            )

    # curated 全体を辞書に反映（レポート外でも有効）
    for alias_key, target in CURATED_ALIASES.items():
        if target in canonicals and alias_key not in data["aliases"]:
            new_aliases[alias_key] = target

    if new_aliases:
        data["aliases"].update(new_aliases)
        data["generated"] = date.today().isoformat()
        note = f" OOV拡張20260703: +{len(new_aliases)} aliases."
        data["notes"] = (str(data.get("notes", "")) + note).strip()
        ALIASES_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    # レポート残りも candidate に追記
    for row in report_rows[100:]:
        skill = row.get("skill", "").strip()
        if not skill:
            continue
        if normalizer.resolve_canonical(normalize_skill_text(skill)):
            continue
        candidates.append(
            {
                "skill": skill,
                "count": row.get("count", ""),
                "source": row.get("source", ""),
                "reason": "OOVレポート101位以降",
                "suggested_canonical": "",
            }
        )

    with NEW_SKILLS_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["skill", "count", "source", "reason", "suggested_canonical"],
        )
        writer.writeheader()
        writer.writerows(candidates)

    print(f"new aliases: {len(new_aliases)}")
    print(f"new_skills_candidate.csv: {len(candidates)} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
