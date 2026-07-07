# -*- coding: utf-8 -*-
"""法人化設計マスター 報酬4軸計算エンジン（2026-07-06確定）。"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import gspread
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SS_ID = "1xSmLwXiDrCVPztSnwhEU1SSBpKOInV5Dx63Zg_mKyR4"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

SES_WORK = Path(__file__).resolve().parents[2]
TOKEN_PATH = SES_WORK / "sheets" / "token_sheets.json"
CREDENTIALS_PATH = SES_WORK / "gmail" / "credentials.json"
BACKUP_DIR = Path(__file__).resolve().parent / "backup"

# --- 営業モデル ---
YEAR1_GROSS_PER_PERSON = 670  # 万/年
YEAR2_GROSS_PER_PERSON = 1170
MONTHLY_STEADY_GROSS = 97.5
MATSUNO_OKAMOTO_MONTHLY = 160  # 万/月（軸2用）
MATSUNO_ANNUAL_GROSS = 1170  # 万/年（定常）
OKAMOTO_ANNUAL_GROSS = 1170
EXEC_COMP_ANNUAL = 360  # 松野役員30万×12（役員報酬前のため除外）
COMMON_FIXED_ANNUAL = 138
VARIABLE_PER_PERSON_ANNUAL = 12
SHAHO_RATE = 0.15
SUBSIDY_PER_PERSON = 64
FLOOR_MONTHLY = 30
DEFICIT_PER_NEW_HIRE = 183
ADMIN_BONUS_RATE = 0.03
FOUNDING_COUNT_DEFAULT = 2  # 岡本・伊波

SCENARIO_COMPANY_TAKE = {
    "262": 262,  # 万/人/年（標準）
    "172": 172,  # 万/人/年（高還元ストレス）
}

HIRE_MIX = {
    "下100": 100,
    "中175": 175,
    "上300": 300,
}

HEAD_COUNTS = [5, 10, 15, 20, 30]
MATRIX_HEAD_COUNTS = list(range(1, 16))
MATRIX_YEARS = 7


def axis1(monthly_gross: float) -> float:
    if monthly_gross < 100:
        return 65.0
    if monthly_gross < 150:
        return 66.0
    if monthly_gross < 200:
        return 67.0
    if monthly_gross < 250:
        return 68.0
    return 69.0


def axis2(monthly_company_gross: float) -> float:
    thresholds = [
        (6000, 3.0),
        (4500, 2.5),
        (3000, 2.0),
        (2000, 1.5),
        (1000, 1.0),
        (500, 0.5),
    ]
    for threshold, bonus in thresholds:
        if monthly_company_gross >= threshold:
            return bonus
    return 0.0


def axis3(year_index: int) -> float:
    if year_index <= 1:
        return 0.0
    return float(min(3, year_index - 1))


def axis4(is_founding: bool) -> float:
    return 5.0 if is_founding else 0.0


def total_rate(
    monthly_person_gross: float,
    monthly_company_gross: float,
    year_index: int,
    is_founding: bool,
    *,
    okamoto_year1_fixed: bool = False,
) -> float:
    if okamoto_year1_fixed:
        return 80.0
    base = axis1(monthly_person_gross)
    bonus2 = axis2(monthly_company_gross)
    bonus3 = axis3(year_index)
    bonus4 = axis4(is_founding)
    raw = base + bonus2 + bonus3 + bonus4
    cap = 80.0 if is_founding else 75.0
    return min(cap, raw)


def monthly_company_gross(num_sales: int, monthly_per_person: float) -> float:
    return num_sales * monthly_per_person + MATSUNO_OKAMOTO_MONTHLY


def annual_gross_per_person(year_index: int) -> float:
    return YEAR1_GROSS_PER_PERSON if year_index == 1 else YEAR2_GROSS_PER_PERSON


def payout_annual(
    annual_gross: float,
    rate_pct: float,
) -> float:
    payout = annual_gross * rate_pct / 100.0
    floor = FLOOR_MONTHLY * 12
    return max(floor, round(payout, 1))


def is_founding_member(index: int, founding_count: int = FOUNDING_COUNT_DEFAULT) -> bool:
    return index < founding_count


@dataclass
class TeamResult:
    ordinary_before_exec: float
    total_payout: float
    total_shaho: float
    admin_bonus: float
    subsidy: float
    deficit: float


def compute_team_ordinary(
    num_sales: int,
    year_index: int,
    *,
    founding_count: int = FOUNDING_COUNT_DEFAULT,
    scenario_key: str = "262",
    hire_mix_key: str = "中175",
    okamoto_year1: bool = False,
) -> TeamResult:
    """役員報酬前経常（万円/年）。成長モデル式（会社取り分ベース）。"""
    take_per = SCENARIO_COMPANY_TAKE[scenario_key]
    year1_take = round(take_per * YEAR1_GROSS_PER_PERSON / YEAR2_GROSS_PER_PERSON, 1)

    if year_index == 1:
        new_n = max(0, num_sales - FOUNDING_COUNT_DEFAULT)
        est = num_sales - new_n
        existing_profit = round(est * YEAR1_GROSS_PER_PERSON * (year1_take / YEAR1_GROSS_PER_PERSON))
        new_profit = round(new_n * YEAR1_GROSS_PER_PERSON * (year1_take / YEAR1_GROSS_PER_PERSON))
        matsuno_gross = 480
        okamoto_gross = 390
    else:
        new_n = 2
        est = max(0, num_sales - new_n)
        take_per = SCENARIO_COMPANY_TAKE[scenario_key]
        existing_profit = round(est * take_per)
        new_profit = round(new_n * year1_take)
        matsuno_gross = MATSUNO_ANNUAL_GROSS
        okamoto_gross = OKAMOTO_ANNUAL_GROSS

    mix = HIRE_MIX.get(hire_mix_key, 175)
    mix_factor = (mix - 175) / 175.0 * 0.05
    subsidy = SUBSIDY_PER_PERSON * (new_n if year_index <= 3 else 0)
    deficit = round(-DEFICIT_PER_NEW_HIRE * new_n * (1 + mix_factor)) if year_index <= 3 else 0

    variable = num_sales * VARIABLE_PER_PERSON_ANNUAL
    common = COMMON_FIXED_ANNUAL
    shaho = round(num_sales * 360 * SHAHO_RATE, 1)

    revenue = (
        existing_profit
        + new_profit
        + matsuno_gross
        + okamoto_gross
        + subsidy
        + deficit
    )
    costs = variable + common + shaho
    ordinary = round(revenue - costs, 1)
    admin_bonus = round(max(0, ordinary) * ADMIN_BONUS_RATE, 1)
    ordinary_before_exec = round(ordinary - admin_bonus, 1)

    # 4軸実効還元（参考: 給与シミュレーション用）
    annual_per = annual_gross_per_person(year_index)
    monthly_per = annual_per / 12.0
    m_company = monthly_company_gross(num_sales, monthly_per)
    total_payout = 0.0
    for i in range(num_sales):
        founding = is_founding_member(i, founding_count)
        y1_fix = okamoto_year1 and founding and i == 0
        rate = total_rate(monthly_per, m_company, year_index, founding, okamoto_year1_fixed=y1_fix)
        total_payout += payout_annual(annual_per, rate)

    return TeamResult(
        ordinary_before_exec=ordinary_before_exec,
        total_payout=round(total_payout, 1),
        total_shaho=shaho,
        admin_bonus=admin_bonus,
        subsidy=subsidy,
        deficit=round(deficit, 1),
    )


def format_profit(value: float) -> str:
    if value < 0:
        return f"({abs(round(value)):,}万)"
    return f"{round(value):,}万"


def build_matrix_table(
    title: str,
    rate_fn,
) -> list[list[str]]:
    rows: list[list[str]] = [
        [title],
        ["人数＼年数"] + [f"{y}年目" for y in range(1, MATRIX_YEARS + 1)],
    ]
    for n in MATRIX_HEAD_COUNTS:
        line = [f"{n}名"]
        for y in range(1, MATRIX_YEARS + 1):
            val = rate_fn(n, y)
            line.append(format_profit(val))
        rows.append(line)
    rows.append([])
    return rows


def matrix_flat_rate(rate_pct: float, n: int, year_index: int) -> float:
    annual_per = annual_gross_per_person(year_index)
    sales_gross = n * annual_per
    payout = n * max(FLOOR_MONTHLY * 12, sales_gross * rate_pct / 100)
    shaho = payout * SHAHO_RATE
    variable = n * VARIABLE_PER_PERSON_ANNUAL
    common = COMMON_FIXED_ANNUAL
    matsuno_okamoto = MATSUNO_ANNUAL_GROSS + OKAMOTO_ANNUAL_GROSS
    ordinary = sales_gross + matsuno_okamoto - payout - shaho - variable - common
    admin = max(0, ordinary) * ADMIN_BONUS_RATE
    return round(ordinary - admin, 1)


def matrix_actual_rate(n: int, year_index: int, founding_count: int) -> float:
    if founding_count <= 0:
        scenario = "262"
    elif founding_count >= n:
        scenario = "172"
    else:
        scenario = "262"
    return compute_team_ordinary(
        n, year_index, founding_count=founding_count, scenario_key=scenario
    ).ordinary_before_exec


def initial_four_steady_ordinary() -> float:
    """岡本150(80%)/伊波80/新規175×2 の定常年間（役員報酬前）≈830〜880万。"""
    existing = 4 * SCENARIO_COMPANY_TAKE["262"]
    mo_net = 220  # 松野・岡本粗利の営業チームへの按分（4名定常）
    variable = 4 * VARIABLE_PER_PERSON_ANNUAL
    common = COMMON_FIXED_ANNUAL
    shaho = round(4 * 360 * SHAHO_RATE, 1)
    ordinary = existing + mo_net - variable - common - shaho
    admin_bonus = round(max(0, ordinary) * ADMIN_BONUS_RATE, 1)
    return round(ordinary - admin_bonus, 1)


def validate_gates() -> None:
    ref = compute_team_ordinary(10, 2, scenario_key="262")
    target = 3600
    low = target * 0.95
    high = target * 1.05
    val = ref.ordinary_before_exec
    if not (low <= val <= high):
        raise SystemExit(
            f"検算NG: 262・10名・2年目 役員報酬前経常={val}万 "
            f"(期待 {target}万 ±5% = {low:.0f}〜{high:.0f}万)"
        )
    init4 = initial_four_steady_ordinary()
    if not (830 <= init4 <= 880):
        raise SystemExit(
            f"検算NG: 初期4名定常={init4}万 (期待 830〜880万)"
        )
    print(f"[検算OK] 262・10名・2年目={val}万 / 初期4名定常={init4}万")


def get_gspread_client() -> gspread.Client:
    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    return gspread.authorize(creds)


def backup_sheet(ws: gspread.Worksheet) -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = BACKUP_DIR / f"{ws.title}_{ts}.json"
    data = ws.get_all_values()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def update_sheet(ws: gspread.Worksheet, rows: list[list], range_name: str) -> None:
    backup_sheet(ws)
    ws.update(values=rows, range_name=range_name)
    time.sleep(1.1)


def salary_simulation_rows() -> list[list]:
    levels = [50, 80, 100, 120, 150, 200, 250]
    rows: list[list] = [
        ["月粗利別 手取りシミュレーション  2026-07-06確定  全単位: 万円/月"],
        ["4軸キャップレス改定。算術上限: 一般75% / 創業80%"],
        [],
        ["■ 通常メンバー（算術上限75%）"],
        ["想定: 全社月粗利1,500万（10名体制）→ 軸2=+1%"],
        ["月粗利", "軸1率", "1年目", "2年目", "3年目", "4年目", "月収上限"],
    ]
    m_company = 1500.0
    for g in levels:
        base = axis1(g)
        payouts = []
        for yi in range(1, 5):
            rate = min(75.0, base + axis2(m_company) + axis3(yi))
            payouts.append(f"{round(g * rate / 100, 1)}万")
        cap = f"{round(g * 0.75, 1)}万"
        rows.append([f"{g}万", f"{base}%"] + payouts + [cap])

    rows.extend([
        [],
        ["■ 創業メンバー（算術上限80%・軸4=+5%込み）"],
        ["想定: 10名体制 → 軸2=+1%, 軸4=+5%"],
        ["月粗利", "軸1率", "1年目", "2年目", "3年目", "4年目", "月収上限"],
    ])
    for g in levels:
        base = axis1(g)
        payouts = []
        for yi in range(1, 5):
            rate = min(80.0, base + axis2(m_company) + axis3(yi) + 5.0)
            payouts.append(f"{round(g * rate / 100, 1)}万")
        cap = f"{round(g * 0.80, 1)}万"
        rows.append([f"{g}万", f"{base}%"] + payouts + [cap])

    rows.extend([
        [],
        ["■ 初期4名タブ（定常・岡本初年度80%固定は1年目のみ）"],
        ["メンバー", "月粗利", "還元", "月収", "年収"],
        ["岡本", "150万", "80%固定", "120.0万", "1,440万"],
        ["伊波", "80万", "4軸適用",
         f"{round(80 * min(80, axis1(80)+axis2(840)+axis3(2)+5)/100, 1)}万", ""],
        ["新規A", "175万", "4軸適用", f"{round(175 * min(75, axis1(175)+axis2(840)+axis3(2))/100, 1)}万", ""],
        ["新規B", "175万", "4軸適用", f"{round(175 * min(75, axis1(175)+axis2(840)+axis3(2))/100, 1)}万", ""],
        [f"★定常 役員報酬前経常（4名合計）", "", "", "", f"約{initial_four_steady_ordinary()}万/年"],
        [],
        ["■ 注記"],
        ["・キャップ条項削除。算術上限のみ（一般75%/創業80%）"],
        ["・岡本初年度のみ80%固定（報酬表適用外）"],
        ["・軸4は岡本・伊波のみ+5%"],
        ["・全社粗利6,000万/月=売却検討ライン（成長モデル参照）"],
    ])
    return rows


def growth_model_rows() -> list[list]:
    rows: list[list] = [
        [],
        ["■ 4名スタート + 年2名追加（2026-07-06確定・4軸キャップレス）  全単位: 万円/年"],
        ["松野=経営者(月30万) / 岡本+伊波+新規2=4名 / 松野岡本粗利=20万→段階増"],
        [
            "年", "営業", "松野粗利", "岡本粗利", "既存会社取分", "新規会社取分",
            "助成金", "共通費", "変動費", "社保", "役員報酬", "赤字回収", "★経常利益",
        ],
    ]
    headcounts = [4, 6, 8, 10, 12, 14, 16]
    matsuno_ann = [480, 720, 960, 1170, 1170, 1170, 1170]
    okamoto_ann = [390, 600, 840, 1170, 1170, 1170, 1170]
    for y in range(7):
        h = headcounts[y]
        new_n = 0 if y == 0 else 2
        est = h - new_n if y > 0 else 4
        if y == 0:
            team = compute_team_ordinary(4, 1, okamoto_year1=True)
            profit = team.ordinary_before_exec - EXEC_COMP_ANNUAL
            existing_profit = round(4 * 670 * 0.25)
            new_profit = 0
            subsidy = 64 * 4
            deficit = round(-183 * 2)
        else:
            team = compute_team_ordinary(h, y + 1)
            profit = team.ordinary_before_exec - EXEC_COMP_ANNUAL
            existing_profit = round(est * 262)
            new_profit = round(new_n * 170)
            subsidy = 64 * new_n
            deficit = round(-183 * new_n)
        common = 138
        variable = h * 12
        shaho = round(h * 360 * 0.15)
        exec_comp = 360
        rows.append([
            f"{y + 1}年目", f"{h}名", matsuno_ann[y], okamoto_ann[y],
            existing_profit, new_profit, subsidy, common, variable, shaho, exec_comp, deficit, profit,
        ])

    rows.extend([
        [],
        ["■ 売却検討ライン（2026-07-06確定）"],
        ["全社月粗利", "6,000万/月", "", "到達時に売却・EXIT検討"],
        ["想定営業", "約55名+", "", "軸2 Max+3%・定常97.5万/人"],
        [],
        ["前提:"],
        ["・4軸キャップレス（算術上限75%/80%）"],
        ["・新規: 年2名。助成金手残り64万/人"],
        ["・新規赤字回収: -183万/人"],
        ["・変動費=人数×12万/年。社保=給与×15%"],
        ["・松野役員報酬: 月30万固定（経常利益から別途控除）"],
    ])
    return rows


def axis_sheet_rows() -> list[list]:
    return [
        ["営業報酬 4軸設計"],
        ["確定版: 2026-07-06（キャップ条項削除・松野確定）"],
        [],
        ["■ 軸1: 個人粗利ティア（1%刻み）", "", "", "", "個人粗利に応じた基本還元"],
        ["月粗利帯", "還元率", "", "", "備考"],
        ["〜99万", "65%", "", "", "T1（下限）"],
        ["100万〜", "66%", "", "", ""],
        ["150万〜", "67%", "", "", ""],
        ["200万〜", "68%", "", "", ""],
        ["250万〜", "69%", "", "", "軸1上限"],
        [],
        ["■ 軸2: 全社粗利ボーナス（0.5%刻み・Max+3%）", "", "", "", "全社成長に連動"],
        ["全社月粗利", "加算率", "", "", "備考"],
        ["500万〜", "+0.5%", "", "", ""],
        ["1,000万〜", "+1.0%", "", "", ""],
        ["2,000万〜", "+1.5%", "", "", ""],
        ["3,000万〜", "+2.0%", "", "", ""],
        ["4,500万〜", "+2.5%", "", "", ""],
        ["6,000万〜", "+3.0%", "", "", "上限・売却検討ライン"],
        [],
        ["■ 軸3: 勤続加算", "", "", "", "継続勤務への還元"],
        ["勤続年数", "加算率", "", "", "備考"],
        ["1年目", "+0%", "", "", ""],
        ["2年目", "+1%", "", "", ""],
        ["3年目", "+2%", "", "", ""],
        ["4年目以降", "+3%", "", "", "上限"],
        [],
        ["■ 軸4: 創業プレミアム", "", "", "", "岡本・伊波のみ"],
        ["対象", "加算率", "", "", "備考"],
        ["岡本・伊波", "+5%", "", "", "人数連動なし・一律"],
        [],
        ["■ 算術上限（キャップ条項は削除）"],
        ["通常メンバー", "75%", "軸1+軸2+軸3の合算上限", "", ""],
        ["創業メンバー", "80%", "軸1+軸2+軸3+軸4の合算上限", "", ""],
        ["岡本初年度", "80%固定", "報酬表適用外", "", "2年目以降は4軸適用（要検討）"],
        [],
        ["■ 合計還元率シミュレーション例（10名・月粗利97.5万）"],
        ["パターン", "軸1", "軸2", "軸3", "軸4", "合計"],
        ["新人1年目", "65%", "+1%", "+0%", "+0%", "66%"],
        ["中堅2年目・通常", "65%", "+1%", "+1%", "+0%", "67%"],
        ["ベテラン4年目・通常", "65%", "+1%", "+3%", "+0%", "69%"],
        ["創業4年目・伊波", "65%", "+1%", "+3%", "+5%", "74%"],
        ["創業4年目・上限近傍", "65%", "+3%", "+3%", "+5%", "80%（上限）"],
    ]


def premise_patch_rows() -> list[list]:
    return [
        [],
        ["■ 報酬4軸キャップレス改定（2026-07-06確定）"],
        ["軸1", "65〜69%（月粗利帯・1%刻み）", "", "旧2%刻みテーブル廃止"],
        ["軸2", "全社月粗利500万〜+0.5%刻み", "Max+3%", "6,000万/月=売却検討ライン"],
        ["軸3", "2年目+1%/年", "Max+3%", "成長条件なし"],
        ["軸4", "岡本・伊波+5%一律", "", "人数連動廃止"],
        ["上限", "一般75%/創業80%", "", "キャップ条項削除・算術上限のみ"],
        ["岡本初年度", "80%固定", "", "報酬表適用外"],
        ["兼任", "レート特例なし", "", "事務対価は手当・ボーナス別建て"],
    ]


def confirmed_items_rows() -> list[list]:
    return [
        ["2026-07-06", "営業報酬 軸1", "65〜69%（1%刻み）。〜99万=65%/100万〜=66%/150万〜=67%/200万〜=68%/250万〜=69%", "確定"],
        ["2026-07-06", "営業報酬 軸2", "全社月粗利0.5%刻みMax+3%。6,000万/月=売却検討ライン", "確定"],
        ["2026-07-06", "営業報酬 軸3", "2年目+1%/年Max+3%（4年目〜）。成長条件廃止", "確定"],
        ["2026-07-06", "営業報酬 軸4", "岡本・伊波のみ一律+5%。人数連動廃止", "確定"],
        ["2026-07-06", "営業報酬 上限", "キャップ条項削除。算術上限: 一般75%/創業80%", "確定"],
    ]
