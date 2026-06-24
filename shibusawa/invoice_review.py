#!/usr/bin/env python3
"""freee ドラフト請求書の自動レビュー（渋沢担当・draft-only）。"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

import requests

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUTH_DIR = os.path.join(ROOT_DIR, "freee_auth")
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if AUTH_DIR not in sys.path:
    sys.path.insert(0, AUTH_DIR)

from token_manager import get_headers

from common.ledger import can_spend
from common.ledger import record as ledger_record

CALLER = "invoice_review"

FREEE_BASE_INV = "https://api.freee.co.jp/iv"
FREEE_UI_URL = "https://secure.freee.co.jp/invoices"
COMPANY_ID = 11712776

PARTNER_BY_ID = {
    91256138: ("株式会社TERRA", "TERRA"),
    113795090: ("株式会社フラップテック", "FT"),
    117422289: ("グレイスライン株式会社", "GL"),
}

REVIEW_CHECKS = [
    "format_check",
    "unit_check",
    "duplicate_check",
    "active_check",
    "withholding_check",
    "anomaly_check",
]

FORMAT_RULES = {
    "TERRA": {
        "subject": r"^\d{4}年\d{1,2}月分請求書$",
        "description_propar": r"^プロパー稼働分$",
        "description_bp": r"^.+様稼働分$",
        "withholding": True,
        "unit": "",
    },
    "FT": {
        "subject": r"^\d{4}年\d{1,2}月分請求書$",
        "description": r"^.+様稼働分$",
        "withholding": False,
        "unit": "",
    },
    "GL": {
        "subject": r"^\d{4}年\d{1,2}月分請求書$",
        "description": r"^.+様\d{1,2}月稼働分$",
        "withholding": False,
        "unit": "",
    },
}

NG_PHRASES = [
    "送信しました",
    "確定しました",
    "発行しました",
    "請求書を送付",
    "freeeで確定",
]


class DraftViolationError(RuntimeError):
    """draft-only 違反（実行宣言検出）。"""


@dataclass
class CheckResult:
    name: str
    ok: bool
    level: str = "OK"
    summary: str = ""
    issues: list[str] = field(default_factory=list)


@dataclass
class ReviewSummary:
    target_month: str
    ok: bool
    checks: list[CheckResult]
    invoices: list[dict[str, Any]]
    invoice_groups: list[dict[str, Any]]
    total_ex_tax: int = 0
    anomalies: list[str] = field(default_factory=list)


def _load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    path = os.path.join(ROOT_DIR, "config", ".env")
    if not os.path.exists(path):
        return env
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def _notify_line(text: str) -> str:
    _validate_draft(text)
    try:
        from line_webhook.line_bridge import push_or_log

        uid = _load_env().get("MATSUNO_LINE_USER_ID", "")
        if uid:
            return push_or_log(uid, text, "invoice_review")
    except Exception as exc:
        print(f"[notify] LINE通知スキップ: {exc}")
    return "logged"


def _validate_draft(result: str) -> None:
    for phrase in NG_PHRASES:
        if phrase in result:
            raise DraftViolationError(f"実行宣言を検出: {phrase}")


def _record_spend(caller: str = CALLER) -> None:
    """LLM未使用の0円コストを記録（CostGuardルール遵守）。"""
    ledger_record(0, 0, "", caller)


def _cost_guard_blocked(notify: bool, dry_run: bool) -> ReviewSummary | None:
    if not can_spend(est_in=0, est_out=0, model=""):
        msg = "【⚠️ CostGuard】日次上限到達。請求書レビューをスキップしました"
        print(msg)
        if notify and not dry_run:
            _notify_line(msg)
        return ReviewSummary(
            target_month="",
            ok=False,
            checks=[CheckResult("cost_guard", False, summary="日次上限到達")],
            invoices=[],
            invoice_groups=[],
        )
    return None


def freee_headers() -> dict[str, str]:
    h = get_headers()
    h["Content-Type"] = "application/json"
    return h


def parse_target_month(target_month: str) -> tuple[int, int]:
    y, m = map(int, target_month.split("-"))
    return y, m


def subject_for_month(year: int, month: int) -> str:
    return f"{year}年{month}月分請求書"


def billing_date_for_month(year: int, month: int) -> str:
    if month == 12:
        nxt = date(year + 1, 1, 1)
    else:
        nxt = date(year, month + 1, 1)
    return nxt.isoformat()


def prev_target_month(target_month: str) -> str:
    y, m = parse_target_month(target_month)
    if m == 1:
        return f"{y - 1}-12"
    return f"{y}-{m - 1:02d}"


def partner_info(invoice: dict[str, Any]) -> tuple[str, str]:
    pid = invoice.get("partner_id")
    if pid in PARTNER_BY_ID:
        return PARTNER_BY_ID[pid]
    name = str(invoice.get("partner_name") or invoice.get("partner_display_name") or f"partner:{pid}")
    if "TERRA" in name:
        return name, "TERRA"
    if "フラップ" in name or "FT" in name:
        return name, "FT"
    if "グレイス" in name or "GL" in name:
        return name, "GL"
    return name, "UNKNOWN"


def payment_bucket_label(invoice: dict[str, Any], partner_type: str) -> str:
    if partner_type == "FT":
        return "45"
    billing = invoice.get("billing_date")
    payment = invoice.get("payment_date")
    if not billing or not payment:
        return "?"
    bd = datetime.strptime(billing, "%Y-%m-%d").date()
    close = bd - timedelta(days=1)
    pd = datetime.strptime(payment, "%Y-%m-%d").date()
    days = (pd - close).days
    if days <= 31:
        return "30"
    if days <= 46:
        return "45"
    return "60"


def invoice_amount_ex_tax(invoice: dict[str, Any]) -> int:
    if invoice.get("amount_excluding_tax") is not None:
        return int(invoice["amount_excluding_tax"])
    sub = 0
    for line in invoice.get("lines") or []:
        if line.get("type") != "item":
            continue
        qty = float(line.get("quantity", 1))
        up = float(str(line.get("unit_price", 0)).replace(",", ""))
        sub += int(qty * up)
    return sub


def count_people_in_invoice(invoice: dict[str, Any]) -> int:
    count = 0
    for line in invoice.get("lines") or []:
        if line.get("type") != "item":
            continue
        desc = str(line.get("description", ""))
        if desc == "プロパー稼働分":
            count += int(float(line.get("quantity", 1)))
        else:
            count += 1
    return count


def fetch_invoices(target_month: str, *, draft_only: bool = True) -> list[dict[str, Any]]:
    year, month = parse_target_month(target_month)
    billing = billing_date_for_month(year, month)
    subject = subject_for_month(year, month)
    results: list[dict[str, Any]] = []
    offset = 0
    while True:
        params: dict[str, Any] = {"company_id": COMPANY_ID, "limit": 100, "offset": offset}
        res = requests.get(f"{FREEE_BASE_INV}/invoices", headers=freee_headers(), params=params, timeout=45)
        if res.status_code != 200:
            raise RuntimeError(f"GET /iv/invoices failed: {res.status_code} {res.text[:200]}")
        batch = res.json().get("invoices") or []
        for inv in batch:
            if inv.get("billing_date") != billing:
                continue
            if inv.get("subject") != subject:
                continue
            if draft_only:
                status = str(inv.get("invoice_status") or inv.get("status") or "").lower()
                sending = str(inv.get("sending_status") or "").lower()
                if status in ("issued", "sent", "submitted") and sending not in ("unsent", ""):
                    continue
            detail = fetch_invoice_detail(inv["id"])
            results.append(detail)
        if len(batch) < 100:
            break
        offset += 100
    return results


def fetch_invoice_detail(invoice_id: int) -> dict[str, Any]:
    res = requests.get(
        f"{FREEE_BASE_INV}/invoices/{invoice_id}",
        headers=freee_headers(),
        params={"company_id": COMPANY_ID},
        timeout=45,
    )
    if res.status_code != 200:
        raise RuntimeError(f"GET invoice/{invoice_id} failed: {res.status_code}")
    return res.json().get("invoice") or {}


def format_check(invoices: list[dict[str, Any]]) -> CheckResult:
    issues: list[str] = []
    for inv in invoices:
        partner_name, ptype = partner_info(inv)
        rules = FORMAT_RULES.get(ptype)
        if not rules:
            issues.append(f"{partner_name}: 未知の取引先タイプ")
            continue
        subject = str(inv.get("subject") or "")
        if not re.match(rules["subject"], subject):
            issues.append(f"{partner_name}: 件名不一致 '{subject}'")
        for line in inv.get("lines") or []:
            if line.get("type") != "item":
                continue
            desc = str(line.get("description") or "")
            if ptype == "TERRA":
                if desc == "プロパー稼働分":
                    if not re.match(rules["description_propar"], desc):
                        issues.append(f"{partner_name}: 摘要不一致 '{desc}'")
                elif not re.match(rules["description_bp"], desc):
                    issues.append(f"{partner_name}: 摘要不一致 '{desc}'")
            elif ptype == "GL":
                if not re.match(rules["description"], desc):
                    issues.append(f"{partner_name}: 摘要不一致 '{desc}'")
            else:
                if not re.match(rules["description"], desc):
                    issues.append(f"{partner_name}: 摘要不一致 '{desc}'")
    return CheckResult(
        "format_check",
        ok=not issues,
        summary="全件OK" if not issues else f"{len(issues)}件NG",
        issues=issues,
    )


def unit_check(invoices: list[dict[str, Any]]) -> CheckResult:
    issues = []
    for inv in invoices:
        partner_name, _ = partner_info(inv)
        for line in inv.get("lines") or []:
            if line.get("type") != "item":
                continue
            unit = line.get("unit")
            if unit not in ("", None):
                issues.append(f"{partner_name}: 単位欄='{unit}' 行={line.get('description')}")
    return CheckResult(
        "unit_check", ok=not issues, summary="全件空欄" if not issues else f"{len(issues)}件NG", issues=issues
    )


def duplicate_check(invoices: list[dict[str, Any]]) -> CheckResult:
    seen: dict[tuple, str] = {}
    issues = []
    for inv in invoices:
        key = (inv.get("partner_id"), inv.get("payment_date"), inv.get("total_amount"))
        label = f"{partner_info(inv)[0]} / {inv.get('invoice_number') or inv.get('id')}"
        if key in seen:
            issues.append(f"重複: {seen[key]} と {label}")
        else:
            seen[key] = label
    return CheckResult(
        "duplicate_check", ok=not issues, summary="なし" if not issues else f"{len(issues)}件", issues=issues
    )


def _names_from_invoice(invoice: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for line in invoice.get("lines") or []:
        desc = str(line.get("description") or "")
        if desc == "プロパー稼働分":
            continue
        m = re.match(r"^(.+?)様(?:\d{1,2}月)?稼働分$", desc)
        if m:
            names.add(m.group(1))
    return names


def active_check(invoices: list[dict[str, Any]], target_month: str) -> CheckResult:
    import sheets_reader as SR

    y, m = parse_target_month(target_month)
    entries, _meta = SR.load_active_entries(target_month=date(y, m, 1))
    expected = {e["name"] for e in entries}
    found: set[str] = set()
    issues: list[str] = []
    for inv in invoices:
        partner_name, ptype = partner_info(inv)
        found |= _names_from_invoice(inv)
        if ptype == "TERRA":
            for line in inv.get("lines") or []:
                if str(line.get("description")) == "プロパー稼働分":
                    qty = int(float(line.get("quantity", 0)))
                    terra_props = sum(1 for e in entries if e.get("source") == "TERRA" and e.get("is_prop"))
                    if qty != terra_props:
                        issues.append(f"TERRA プロパー: 請求書{qty}名 vs Sheet{terra_props}名")
    missing = sorted(expected - found)
    extra = sorted(found - expected)
    if missing:
        issues.append(f"請求書に無い稼働確定者: {', '.join(missing[:10])}")
    if extra:
        issues.append(f"Sheetに無い請求明細: {', '.join(extra[:10])}")
    return CheckResult(
        "active_check",
        ok=not issues,
        summary="全件一致" if not issues else "不一致あり",
        issues=issues,
    )


def withholding_check(invoices: list[dict[str, Any]]) -> CheckResult:
    issues = []
    for inv in invoices:
        partner_name, ptype = partner_info(inv)
        expected = FORMAT_RULES.get(ptype, {}).get("withholding")
        if expected is None:
            continue
        for line in inv.get("lines") or []:
            if line.get("type") != "item":
                continue
            wh = bool(line.get("withholding"))
            if wh != expected:
                issues.append(f"{partner_name}: {line.get('description')} withholding={wh} 期待={expected}")
    return CheckResult(
        "withholding_check",
        ok=not issues,
        summary="全件正常" if not issues else f"{len(issues)}件NG",
        issues=issues,
    )


def group_amounts(invoices: list[dict[str, Any]]) -> dict[tuple[str, str], int]:
    groups: dict[tuple[str, str], int] = {}
    for inv in invoices:
        partner_name, ptype = partner_info(inv)
        bucket = payment_bucket_label(inv, ptype)
        key = (partner_name, bucket)
        groups[key] = groups.get(key, 0) + invoice_amount_ex_tax(inv)
    return groups


def anomaly_check(current_invoices: list[dict[str, Any]], prev_invoices: list[dict[str, Any]]) -> CheckResult:
    current = group_amounts(current_invoices)
    prev = group_amounts(prev_invoices)
    issues: list[str] = []
    anomalies: list[str] = []
    for key, amt in current.items():
        prev_amt = prev.get(key)
        if not prev_amt:
            continue
        pct = (amt - prev_amt) / prev_amt * 100
        label = f"{key[0].replace('株式会社', '')}({key[1]}日)"
        if abs(pct) > 50:
            msg = f"{label} 前月比{pct:+.0f}%（個別確認）"
            issues.append(msg)
            anomalies.append(f"ALERT: {msg}")
        elif abs(pct) > 20:
            msg = f"{label} 前月比{pct:+.0f}%（要確認）"
            issues.append(msg)
            anomalies.append(f"WARNING: {msg}")
    return CheckResult(
        "anomaly_check",
        ok=not issues,
        level="WARNING" if issues else "OK",
        summary="異常なし" if not issues else f"{len(issues)}件",
        issues=issues,
    )


def build_invoice_groups(invoices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for inv in invoices:
        partner_name, ptype = partner_info(inv)
        short = partner_name.replace("株式会社", "").replace("グレイスライン", "グレイスライン")
        bucket = payment_bucket_label(inv, ptype)
        groups.append(
            {
                "partner": partner_name,
                "short": short,
                "bucket": bucket,
                "people": count_people_in_invoice(inv),
                "amount": invoice_amount_ex_tax(inv),
                "invoice_id": inv.get("id"),
                "invoice_number": inv.get("invoice_number"),
            }
        )
    return sorted(groups, key=lambda g: (g["partner"], int(g["bucket"]) if g["bucket"].isdigit() else 99))


def format_success_line_message(summary: ReviewSummary) -> str:
    y, m = parse_target_month(summary.target_month)
    lines = [f"【{y}年{m}月分 請求書ドラフトレビュー完了】", ""]
    labels = {
        "format_check": "フォーマット",
        "unit_check": "単位欄",
        "duplicate_check": "重複",
        "active_check": "稼働整合",
        "withholding_check": "源泉徴収",
        "anomaly_check": "異常検知",
    }
    for chk in summary.checks:
        label = labels.get(chk.name, chk.name)
        if chk.ok:
            lines.append(f"✅ {label}: {chk.summary}")
        elif chk.name == "anomaly_check":
            lines.append(f"⚠️ {label}: {chk.summary}")
            for issue in chk.issues:
                lines.append(f"   {issue}")
        else:
            lines.append(f"❌ {label}: {chk.summary}")
    lines.extend(["", "請求書一覧:"])
    for g in summary.invoice_groups:
        lines.append(f"・{g['short']}({g['bucket']}日): {g['people']}名 / ¥{g['amount']:,}")
    lines.extend(
        ["", f"合計: ¥{summary.total_ex_tax:,}（税抜）", "", "明日(2日)freee UIでご確認ください", FREEE_UI_URL]
    )
    return "\n".join(lines)


def format_ng_line_message(summary: ReviewSummary) -> str:
    lines = ["【⚠️ 請求書レビュー NG】", ""]
    for chk in summary.checks:
        if chk.ok:
            continue
        lines.append(f"❌ {chk.name}: {chk.summary}")
        for issue in chk.issues[:5]:
            lines.append(f"  対象: {issue}")
    lines.extend(["", "freee UIで修正後、再レビューコマンドを実行:", "python shibusawa/invoice_review.py --recheck"])
    return "\n".join(lines)


def sample_invoices_demo() -> list[dict[str, Any]]:
    """dry-run デモ用サンプル（API未取得時）。"""
    return [
        {
            "id": 1,
            "partner_id": 91256138,
            "billing_date": "2026-08-01",
            "payment_date": "2026-09-14",
            "subject": "2026年7月分請求書",
            "total_amount": 500000,
            "lines": [
                {
                    "type": "item",
                    "description": "プロパー稼働分",
                    "quantity": 14,
                    "unit": "",
                    "unit_price": "15000",
                    "withholding": True,
                },
                {
                    "type": "item",
                    "description": "芹澤様稼働分",
                    "quantity": 1,
                    "unit": "",
                    "unit_price": "45000",
                    "withholding": True,
                },
            ],
        },
        {
            "id": 2,
            "partner_id": 91256138,
            "billing_date": "2026-08-01",
            "payment_date": "2026-09-29",
            "subject": "2026年7月分請求書",
            "total_amount": 300000,
            "lines": [
                {
                    "type": "item",
                    "description": "プロパー稼働分",
                    "quantity": 8,
                    "unit": "",
                    "unit_price": "15000",
                    "withholding": True,
                },
            ],
        },
        {
            "id": 3,
            "partner_id": 113795090,
            "billing_date": "2026-08-01",
            "payment_date": "2026-09-14",
            "subject": "2026年7月分請求書",
            "total_amount": 400000,
            "lines": [
                {
                    "type": "item",
                    "description": "笠井健太様稼働分",
                    "quantity": 1,
                    "unit": "",
                    "unit_price": "68000",
                    "withholding": False,
                },
            ],
        },
    ]


def run_review(
    target_month: str,
    *,
    dry_run: bool = False,
    notify: bool = True,
    invoices: list[dict[str, Any]] | None = None,
    prev_invoices: list[dict[str, Any]] | None = None,
) -> ReviewSummary:
    needs_freee_api = invoices is None or prev_invoices is None
    if needs_freee_api:
        blocked = _cost_guard_blocked(notify, dry_run)
        if blocked is not None:
            blocked.target_month = target_month
            return blocked

    use_sample = False
    if invoices is None:
        try:
            invoices = fetch_invoices(target_month, draft_only=True)
        except Exception as exc:
            if dry_run:
                print(f"[dry-run] freee API未取得: {exc} → サンプルデータで表示")
                invoices = sample_invoices_demo()
                use_sample = True
            else:
                raise
    if dry_run and not invoices:
        print("[dry-run] ドラフト0件 → サンプルデータで表示")
        invoices = sample_invoices_demo()
        use_sample = True
    if prev_invoices is None and not use_sample:
        prev_invoices = fetch_invoices(prev_target_month(target_month), draft_only=False)
    elif prev_invoices is None:
        prev_invoices = []

    checks = [
        format_check(invoices),
        unit_check(invoices),
        duplicate_check(invoices),
    ]
    if use_sample:
        checks.append(CheckResult("active_check", True, summary="サンプル（スキップ）"))
    else:
        checks.append(active_check(invoices, target_month))
    checks.extend(
        [
            withholding_check(invoices),
            anomaly_check(invoices, prev_invoices),
        ]
    )
    groups = build_invoice_groups(invoices)
    total = sum(g["amount"] for g in groups)
    hard_ng = [c for c in checks if not c.ok and c.name != "anomaly_check"]
    ok = not hard_ng

    summary = ReviewSummary(
        target_month=target_month,
        ok=ok,
        checks=checks,
        invoices=invoices,
        invoice_groups=groups,
        total_ex_tax=total,
        anomalies=[i for c in checks if c.name == "anomaly_check" for i in c.issues],
    )

    message = format_success_line_message(summary) if ok else format_ng_line_message(summary)
    _validate_draft(message)
    print(message)
    if notify and not dry_run:
        _notify_line(message)
    if needs_freee_api:
        _record_spend(CALLER)
    return summary


def run_recheck(target_month: str | None = None, *, dry_run: bool = False) -> ReviewSummary:
    month = target_month or _default_month()
    return run_review(month, dry_run=dry_run, notify=not dry_run)


def _default_month() -> str:
    today = date.today()
    return f"{today.year}-{today.month:02d}"


def main() -> None:
    parser = argparse.ArgumentParser(description="freee請求書ドラフトレビュー（渋沢）")
    parser.add_argument("--month", help="対象月 YYYY-MM")
    parser.add_argument("--dry-run", action="store_true", help="LINE通知なし・結果表示のみ")
    parser.add_argument("--recheck", action="store_true", help="再レビュー")
    args = parser.parse_args()
    month = args.month or _default_month()
    run_review(month, dry_run=args.dry_run, notify=not args.dry_run)


if __name__ == "__main__":
    main()
