# -*- coding: utf-8 -*-
"""Phase 8A: 有価証券報告書PDFから財務・人員データを抽出"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pdfplumber

COMPANY_PDFS: dict[str, dict[str, str]] = {
    "6028": {
        "company_name": "テクノプロHD",
        "pdf_url": "https://www.technoproholdings.com/ir/pdf/2025-49.pdf",
        "ir_page": "https://www.technoproholdings.com/ir/ir_library/securities_report.html",
    },
    "4641": {
        "company_name": "アルプス技研",
        "pdf_url": "https://www.alpsgiken.co.jp/ir/library/pdf/report/ir20260325.pdf",
        "ir_page": "https://www.alpsgiken.co.jp/ir/library/report.html",
    },
    "2458": {
        "company_name": "夢テクノロジー",
        "pdf_url": "https://f.irbank.net/pdf/E05520/ir/S100Q8HD.pdf",
        "ir_page": "https://irbank.net/E05520",
        "fallback_pdf": "https://f.irbank.net/pdf/E05520/ir/S1003P0F.pdf",
    },
    "9749": {
        "company_name": "富士ソフト",
        "pdf_url": "https://www.fsi.co.jp/ir/library/docs/securities_report/55yuuka.pdf",
        "ir_page": "https://www.fsi.co.jp/ir/library/securities_report.html",
    },
    "3626": {
        "company_name": "TIS",
        "pdf_url": "https://www.tisi.jp/documents/jp/ir/finance/securities_report/report_2025_2.pdf",
        "ir_page": "https://www.tisi.jp/ir/finance/securities_report/",
    },
    "9719": {
        "company_name": "SCSK",
        "pdf_url": "https://www.scsk.jp/ir/library/valuable/pdf/scsk/yuho202603_4Q.pdf",
        "ir_page": "https://www.scsk.jp/ir/library/valuable/index.html",
    },
}


def extract_pdf_text(pdf_path: Path, max_pages: int | None = None) -> str:
    parts: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        pages = pdf.pages if max_pages is None else pdf.pages[:max_pages]
        for pg in pages:
            parts.append(pg.extract_text() or "")
    return "\n".join(parts)


def parse_oku_man_yen(text: str) -> int | None:
    m = re.search(r"(\d{1,4}(?:,\d{3})*)億(\d{1,3})百万", text)
    if m:
        oku = int(m.group(1).replace(",", ""))
        return oku * 100 + int(m.group(2))
    m2 = re.search(r"(\d{1,3}(?:,\d{3})+)\s*百万", text)
    if m2:
        return int(m2.group(1).replace(",", ""))
    return None


def to_int_num(s: str) -> int | None:
    m = re.search(r"(-?\d{1,3}(?:,\d{3})+|-?\d+)", s.replace("，", ","))
    if not m:
        return None
    return int(m.group(1).replace(",", ""))


def extract_revenue(text: str) -> int | None:
    candidates: list[int] = []
    for line in text.splitlines():
        if "セグメント" in line and "売上" in line:
            continue
        if any(k in line for k in ("当連結会計年度", "当社グループ", "連結会計年度の業績")) and "売上" in line:
            v = parse_oku_man_yen(line)
            if v:
                candidates.append(v)
        if "売上高" in line and "億" in line and any(k in line for k in ("当連結", "当社", "連結会計年度", "当連結会計")):
            v = parse_oku_man_yen(line)
            if v:
                candidates.append(v)
        m2 = re.search(r"売上高は[、,]?前年度比[^\d]{0,50}(\d{1,3}(?:,\d{3})+)\s*百万", line)
        if m2:
            candidates.append(int(m2.group(1).replace(",", "")))
        m3 = re.search(r"売上高(\d{1,3}(?:,\d{3})+)\s*百万円", line)
        if m3 and "当連結" in line:
            candidates.append(int(m3.group(1).replace(",", "")))
        m4 = re.search(r"売上高は[^\d]{0,20}(\d{1,3}(?:,\d{3})+)\s*百万円", line)
        if m4 and "前年度" in line:
            candidates.append(int(m4.group(1).replace(",", "")))
    candidates = [c for c in candidates if c > 10_000]
    return max(candidates) if candidates else None


def extract_personnel_cost(text: str, revenue: int | None) -> tuple[int | None, str]:
    notes: list[str] = []
    for line in text.splitlines():
        if ("従業員給与" in line and "賞与" in line) or "従業員給与・賞与" in line:
            nums = [int(x.replace(",", "")) for x in re.findall(r"\d{1,3}(?:,\d{3})+", line)]
            nums = [n for n in nums if 5_000 < n < 200_000]
            if nums:
                return max(nums), "従業員給与・賞与(百万円)"
        if "給料及び賞与" in line and "役員" not in line:
            nums = [int(x.replace(",", "")) for x in re.findall(r"\d{1,3}(?:,\d{3})+", line)]
            nums = [n for n in nums if 5_000 < n < 200_000]
            if nums:
                return max(nums), "給料及び賞与(百万円)"

    for line in text.splitlines():
        if "人件費" in line and "率" not in line and "構成" not in line and "退職" not in line:
            nums = [int(x.replace(",", "")) for x in re.findall(r"\d{1,3}(?:,\d{3})+", line)]
            nums = [n for n in nums if 5_000 < n < 200_000]
            if nums:
                return max(nums), "連結人件費(販管費内訳)"

    sga_million: list[int] = []
    for line in text.splitlines():
        if "販売費及び一般管理費" in line and "内訳" not in line:
            nums = [int(x.replace(",", "")) for x in re.findall(r"\d{1,3}(?:,\d{3})+", line)]
            for n in nums:
                if 1_000 < n < 300_000:
                    sga_million.append(n)
                elif 500_000 < n < 50_000_000:
                    sga_million.append(n // 1000)
    if sga_million and revenue:
        valid: list[int] = []
        for n in sga_million:
            if n < revenue:
                valid.append(n)
            elif n // 1000 < revenue:
                valid.append(n // 1000)
        if valid:
            sga = max(valid)
            est = int(sga * 0.65)
            notes.append(f"販管費{sga}百万円の65%で人件費推計")
            return est, "; ".join(notes)
    return None, ""


def extract_employee_count(text: str) -> int | None:
    m = re.search(r"連結従業員数[^\d]{0,40}(\d[\d,]+)\s*人", text)
    if m:
        return int(m.group(1).replace(",", ""))

    m2 = re.search(
        r"従業員数\s+(\d[\d,]+)\s+(\d[\d,]+)\s+(\d[\d,]+)\s+(\d[\d,]+)\s+(\d[\d,]+)",
        text,
    )
    if m2:
        return int(m2.group(5).replace(",", ""))

    m2b = re.search(r"従業員数\s*\(連\)\s*(\d[\d,]+)", text)
    if m2b:
        return int(m2b.group(1).replace(",", ""))

    for line in text.splitlines():
        if re.match(r"^従業員数\s", line.strip()):
            nums = [int(x.replace(",", "")) for x in re.findall(r"\d{1,3}(?:,\d{3})+", line)]
            nums = [n for n in nums if 1_000 < n < 500_000]
            if nums:
                return max(nums)

    chunk_idx = text.find("従業員の状況")
    if chunk_idx >= 0:
        chunk = text[chunk_idx : chunk_idx + 1500]
        m3 = re.search(r"計\s+(\d[\d,]+)\s+\[", chunk)
        if m3:
            return int(m3.group(1).replace(",", ""))
    return None


def extract_sales_staff_count(text: str, employee_count: int | None) -> tuple[int | None, str]:
    notes: list[str] = []
    m = re.search(r"全社[（(]共通[）)]\s*(\d[\d,]+)", text)
    if m:
        return int(m.group(1).replace(",", "")), "全社(共通)を営業/管理部門とみなす"

    m2 = re.search(r"営業管理職員\s+(\d[\d,]+)", text)
    if m2:
        return int(m2.group(1).replace(",", "")), "営業管理職員"

    chunk_idx = text.find("従業員の状況")
    if chunk_idx >= 0:
        chunk = text[chunk_idx : chunk_idx + 2000]
        for label in ("営業", "販売", "管理"):
            m3 = re.search(rf"{label}[^\d]{{0,20}}(\d[\d,]+)", chunk)
            if m3:
                val = int(m3.group(1).replace(",", ""))
                if 20 < val < 50_000:
                    return val, f"従業員状況表の{label}人数"

    if employee_count:
        est = max(int(employee_count * 0.08), 50)
        notes.append("明示記載なし:連結従業員の8%で推計")
        return est, "; ".join(notes)
    return None, ""


def extract_segment_notes(text: str) -> str:
    segs: list[str] = []
    keywords = [
        "技術者派遣",
        "SES",
        "アウトソーシング",
        "受託",
        "エンジニアリング",
        "オフショアリング",
        "ITサービス",
        "ソリューション",
    ]
    for line in text.splitlines():
        for kw in keywords:
            if kw in line:
                v = parse_oku_man_yen(line)
                if not v:
                    m = re.search(rf"{re.escape(kw)}[^\d]{{0,50}}(\d{{1,3}}(?:,\d{{3}})+)", line)
                    if m:
                        raw = int(m.group(1).replace(",", ""))
                        v = raw // 1000 if raw > 1_000_000 else raw
                if v and v > 10:
                    segs.append(f"{kw}:{v}百万円")
                    break
        if len(segs) >= 4:
            break
    return " | ".join(segs[:4])


def analyze_pdf(company: dict[str, str], pdf_path: Path, pdf_url: str, crawl_date: str) -> dict[str, Any]:
    text = extract_pdf_text(pdf_path)
    revenue = extract_revenue(text)
    personnel_cost, p_note = extract_personnel_cost(text, revenue)
    employee_count = extract_employee_count(text)
    sales_staff_count, s_note = extract_sales_staff_count(text, employee_count)
    segment_notes = extract_segment_notes(text)

    sales_personnel_cost: float | None = None
    cost_per_sales: float | None = None
    sales_ratio: float | None = None
    notes: list[str] = []
    if p_note:
        notes.append(p_note)
    if s_note:
        notes.append(s_note)

    if personnel_cost and sales_staff_count:
        if "全社(共通)" in s_note:
            sales_personnel_cost = float(personnel_cost)
            cost_per_sales = personnel_cost / sales_staff_count
            notes.append("全社(共通)に販管費人件費を帰属")
        elif employee_count:
            sales_personnel_cost = personnel_cost * (sales_staff_count / employee_count)
            cost_per_sales = sales_personnel_cost / sales_staff_count
            notes.append("営業人件費=連結人件費×(営業管理部門人数/全従業員)")
        else:
            sales_personnel_cost = float(personnel_cost)
            cost_per_sales = personnel_cost / sales_staff_count
            notes.append("営業管理部門人数のみ:人件費全額を営業按分と仮定")

    if sales_personnel_cost and revenue:
        sales_ratio = sales_personnel_cost / revenue

    return {
        "company_name": company["company_name"],
        "ticker": company.get("ticker", ""),
        "revenue": revenue if revenue is not None else "",
        "personnel_cost": personnel_cost if personnel_cost is not None else "",
        "employee_count": employee_count if employee_count is not None else "",
        "sales_staff_count": sales_staff_count if sales_staff_count is not None else "",
        "cost_per_sales_person": round(cost_per_sales, 2) if cost_per_sales else "",
        "sales_cost_ratio": round(sales_ratio, 4) if sales_ratio else "",
        "ir_pdf_url": pdf_url,
        "segment_revenue_notes": segment_notes,
        "crawl_date": crawl_date,
        "notes": "; ".join(notes),
    }
