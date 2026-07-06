# -*- coding: utf-8 -*-
"""法人化設計マスター 2026-07-02 確定事項 一括修正"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import time
import gspread
from google.oauth2.service_account import Credentials

CREDS_PATH = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\google_credentials.json'
SS_ID = '1xSmLwXiDrCVPztSnwhEU1SSBpKOInV5Dx63Zg_mKyR4'
SCOPES = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

creds = Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPES)
gc = gspread.authorize(creds)
ss = gc.open_by_key(SS_ID)

# ============================================================
# 1. 前提条件シート A15から書き込み
# ============================================================
ws = ss.worksheet('前提条件')
task1_rows = [
    ['■ 還元率上下限（2026-07-02確定）'],
    ['営業下限（T1）', '65%'],
    ['通常メンバー上限', '75%'],
    ['創業メンバー上限', '80%'],
    [''],
    ['■ 1人あたり年間経常（万円）'],
    ['', '65%', '75%', '80%'],
    ['1年目（立上期）', '157万', '95万', '58万'],
    ['2年目以降（定常）', '283.5万', '148.9万', '81.6万'],
    [''],
    ['■ 創業メンバー赤字ライン（2026-07-02確定）'],
    ['会社取り分', '月粗利×20%', '', '創業メンバー上限80%時'],
    ['コスト', '変動費1万+社保(粗利×12%)', '', ''],
    ['赤字ライン', '月粗利12.5万以下', '', '会社取り分2.5万 < コスト約2.5万'],
    ['実質赤字ライン', '月粗利25万未満', '', '最低保証30万との差額で実質赤字'],
    [''],
    ['■ コスト構造（2026-07-02確定）'],
    ['変動費/人/月', '1', '万円', 'PC償却5千+携帯半数貸与1.5千+ライセンス1.5千+雑費2千'],
    ['事務手当', '契約1件×1,000円/月', '', ''],
    ['事務ボーナス', '経常利益の3%', '', '仮置き'],
    ['共通固定費', '前半9万/後半14万', '', '年138万'],
    ['旧「販管費16万/人」は廃止', '', '', '変動費1万+社保に分離'],
]
ws.update(values=task1_rows, range_name='A15')
print('[1/7] 前提条件: 還元率・赤字ライン・コスト構造 修正 OK')
time.sleep(1)

# ============================================================
# 2. 前提条件シート A38から書き込み（初期体制）
# ============================================================
task2_rows = [
    [''],
    ['■ 初期体制（2026-07-02確定）'],
    ['初期メンバー数（松野除く）', '4', '名', '伊波・岡本+新規2名'],
    ['松野役員報酬', '30', '万円/月', '固定+事前確定届出給与で年1調整'],
    ['岡本初年度報酬', '30', '万円/月', '営業メンバーと同位置づけ'],
    ['新規社員固定給', '30', '万円/月', '有期6ヶ月→正社員転換（旧35万から変更）'],
    ['給与下限保証', '30', '万円/月', '赤字人員は事務配転で対応'],
    ['社員給与サイト', '45', '日', '初期。安定後短縮検討'],
    ['公庫融資', '800', '万円', '運転資金（支払いサイト対策）'],
    ['松野/岡本 法人粗利スタート', '20', '万円', '順次付替え（初期は個人事業に残す）'],
    ['TERRA/GL契約', '個人事業で継続', '', 'プロパー扱い・元社員のため'],
    ['助成金手残り', '64', '万円/人', '80万-社労士報酬20%'],
    [''],
    ['■ 組織方針（2026-07-02確定）'],
    ['赤字人員', '事務配転', '', '営業粗利不足時は事務業務へシフト'],
    ['事務2人目', '営業兼任', '', '専属採用は営業10名前後まで不要'],
    ['事務増員ライン', '営業10名前後', '', '経常利益1000万超で検討'],
]
ws.update(values=task2_rows, range_name='A38')
print('[2/7] 前提条件: 初期体制・組織方針 更新 OK')
time.sleep(1)

# ============================================================
# 3. 離職インパクトシート 全面書き直し
# ============================================================
ws3 = ss.worksheet('離職インパクト')
ws3.clear()
task3_rows = [
    ['離職インパクト分析（1名離職時）  2026-07-02確定'],
    ['コスト: 変動費12万/年+社保（給与15%）。旧販管費16万は廃止'],
    [''],
    ['■ 在籍時の年間会社利益（定常・2年目以降）'],
    ['', '65%', '75%', '80%'],
    ['年間粗利/人', '1,170万', '1,170万', '1,170万'],
    ['還元率', '65%', '75%', '80%'],
    ['会社取り分率', '35%', '25%', '20%'],
    ['会社取り分額', '409.5万', '292.5万', '234万'],
    ['変動費/年', '12万', '12万', '12万'],
    ['社保（給与15%）', '114.1万', '131.6万', '140.4万'],
    ['★在籍時年間会社利益', '283.5万', '148.9万', '81.6万'],
    [''],
    ['■ 離職後1年のコスト'],
    ['', '65%', '75%', '80%'],
    ['採用空白期間', '2ヶ月', '2ヶ月', '2ヶ月'],
    ['空白期間ロス', '68万', '49万', '41万'],
    ['採用コスト', '0万', '0万', '0万'],
    ['', '', '', 'リファラル採用のため'],
    ['赤字回収（6ヶ月やり直し）', '110万', '102万', '98万'],
    ['★離職コスト合計', '178万', '151万', '139万'],
    [''],
    ['■ 年間純損失（在籍時利益 − 離職年実質利益）'],
    ['', '65%', '75%', '80%'],
    ['在籍時年間利益', '283.5万', '148.9万', '81.6万'],
    ['離職年の実質利益', '83万', '(51万)', '(57万)'],
    ['★★ 離職による年間純損失', '200万', '約200万', '139万'],
    [''],
    ['■ 示唆'],
    ['・75%還元でも離職1名で年間約200万の純損失'],
    ['・リテンション投資の回収期間: プレミアム差額÷離職損失で試算'],
    ['・最低保証30万+事務配転で赤字人員の離職リスクを低減'],
]
ws3.update(values=task3_rows, range_name='A1')
print('[3/7] 離職インパクト: 全面書き直し OK')
time.sleep(1)

# ============================================================
# 4. 初年度月次PLシート A63から書き込み
# ============================================================
ws4 = ss.worksheet('初年度月次PL')

matsuno = [20, 20, 30, 30, 40, 40, 50, 50, 60, 60, 70, 70]
okamoto = [20, 20, 25, 25, 30, 30, 35, 35, 40, 40, 45, 45]
iwa = [0, 0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 97.5]
new2 = [0, 0, 0, 0, 20, 40, 60, 80, 100, 120, 140, 160]
months = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']


def new2_pay(month_idx, gross_per_person):
    if month_idx < 6:
        return 60
    per_person = max(30, round(gross_per_person * 0.65, 1))
    return round(per_person * 2, 1)


pl_rows = [
    [''],
    ['■ 松野岡本20万スタート（段階付替え）【2026-07-02確定ケース】  全単位: 万円/月'],
    ['松野=経営者(月30万固定) / 岡本(30万固定) / 伊波(30万下限) / 新規2名(有期30万×2→粗利連動)'],
    ['月', '松野粗利', '岡本粗利', '伊波粗利', '新規2名粗利', '粗利合計',
     '松野役報', '岡本給与', '伊波報酬', '新規2名給与', '社保15%', '共通固定', '変動費', 'コスト計', '月次損益', '累積損益'],
]

cumulative = 0
monthly_profits = []
for i, m in enumerate(months):
    total_gross = matsuno[i] + okamoto[i] + iwa[i] + new2[i]
    exec_pay = 30
    oka_pay = 30
    iwa_pay = max(30, round(iwa[i] * 0.65, 1)) if iwa[i] > 0 else 30
    per_person_gross = new2[i] / 2 if new2[i] > 0 else 0
    new2_p = new2_pay(i, per_person_gross)
    total_pay = exec_pay + oka_pay + iwa_pay + new2_p
    shaho = round(total_pay * 0.15, 1)
    common = 9 if i < 6 else 14
    variable = 4
    total_cost = round(total_pay + shaho + common + variable, 1)
    profit = round(total_gross - total_cost, 1)
    cumulative = round(cumulative + profit, 1)
    monthly_profits.append(profit)
    pl_rows.append([
        m, matsuno[i], okamoto[i], iwa[i], new2[i], total_gross,
        exec_pay, oka_pay, iwa_pay, new2_p, shaho, common, variable, total_cost, profit, cumulative,
    ])

ann_gross = sum(matsuno) + sum(okamoto) + sum(iwa) + sum(new2)
ann_exec = 360
ann_oka = 360
ann_iwa = sum(max(30, round(iwa[i] * 0.65, 1)) if iwa[i] > 0 else 30 for i in range(12))
ann_new2 = sum(new2_pay(i, new2[i] / 2 if new2[i] > 0 else 0) for i in range(12))
ann_pay = ann_exec + ann_oka + ann_iwa + ann_new2
ann_shaho = round(ann_pay * 0.15, 1)
ann_common = 138
ann_var = 48
ann_cost = round(ann_pay + ann_shaho + ann_common + ann_var, 1)
ann_profit = round(ann_gross - ann_cost, 1)
subsidy = 256

pl_rows.append([''])
pl_rows.append([
    '年間合計', sum(matsuno), sum(okamoto), sum(iwa), sum(new2), ann_gross,
    ann_exec, ann_oka, round(ann_iwa, 1), round(ann_new2, 1),
    ann_shaho, ann_common, ann_var, ann_cost, ann_profit, '',
])
pl_rows.append(['★経常利益（助成金込み）', round(ann_profit + subsidy)])
pl_rows.append(['★経常利益（助成金なし）', ann_profit])

ws4.update(values=pl_rows, range_name='A63')
print(f'[4/7] 初年度月次PL: 20万スタート更新 OK  経常(助成金込み)={round(ann_profit + subsidy)}万 / なし={ann_profit}万')
time.sleep(1)

# ============================================================
# 5. 成長モデルシート A45から書き込み
# ============================================================
ws5 = ss.worksheet('成長モデル')

headcounts = [4, 6, 8, 10, 12, 14, 16]
matsuno_ann = [480, 720, 960, 1170, 1170, 1170, 1170]
okamoto_ann = [390, 600, 840, 1170, 1170, 1170, 1170]
DEFICIT_PER_PERSON = 183
NEW_PER_YEAR = 2

growth_rows = [
    [''],
    ['■ 4名スタート + 年2名追加（2026-07-02確定ケース）  全単位: 万円/年'],
    ['松野=経営者(月30万) / 岡本+伊波+新規2名=4名 / 松野岡本粗利=20万→段階増'],
    ['年', '営業', '松野粗利', '岡本粗利', '既存会社取分25%', '新規会社取分25%',
     '助成金', '共通費', '変動費', '社保', '役員報酬', '赤字回収', '★経常利益'],
]

for y in range(7):
    h = headcounts[y]
    new_n = NEW_PER_YEAR if y > 0 else 0
    est = h - new_n if y > 0 else 4

    if y == 0:
        existing_profit = round(4 * 670 * 0.25)
        new_profit = 0
        subsidy = 64 * 4
        deficit = round(-DEFICIT_PER_PERSON * 2)
    else:
        existing_profit = round(est * 1170 * 0.25)
        new_profit = round(new_n * 670 * 0.25)
        subsidy = 64 * new_n
        deficit = round(-DEFICIT_PER_PERSON * new_n)

    common = 138
    variable = h * 12
    shaho = round(h * 360 * 0.15)
    exec_comp = 360

    profit = (
        existing_profit + new_profit + matsuno_ann[y] + okamoto_ann[y]
        + subsidy + deficit - common - variable - shaho - exec_comp
    )

    growth_rows.append([
        f'{y + 1}年目', f'{h}名', matsuno_ann[y], okamoto_ann[y],
        existing_profit, new_profit, subsidy, common, variable, shaho, exec_comp, deficit, profit,
    ])

growth_rows.extend([
    [''],
    ['前提:'],
    ['・松野/岡本法人粗利: 20万スタート→段階付替え'],
    ['・営業: 75%還元。会社取り分=粗利×25%'],
    ['・新規: 年2名。有期6ヶ月→正社員転換。助成金手残り64万/人'],
    ['・新規赤字回収: -183万/人×2名（有期6ヶ月の立上りコスト）'],
    ['・変動費=人数×12万/年。社保=人数×360万×15%'],
    ['・松野役員報酬: 月30万固定（年360万）'],
])

ws5.update(values=growth_rows, range_name='A45')
print('[5/7] 成長モデル: 4名スタート+年2名追加 更新 OK')
time.sleep(1)

# ============================================================
# 6. 確定事項一覧シート A44から5行追加
# ============================================================
ws6 = ss.worksheet('確定事項一覧')
task6_rows = [
    ['2026-07-02', '給与下限', '全員30万/月下限保証。赤字人員は事務配転', '確定'],
    ['2026-07-02', '変動費', '月1万/人に修正（旧2万）', '確定'],
    ['2026-07-02', '助成金', '手残り64万/人（80万-社労士20%）', '確定'],
    ['2026-07-02', '事務方針', '赤字人員は事務配転。2人目事務は営業兼任', '確定'],
    ['2026-07-02', '事務ボーナス', '経常利益の3%（仮置き）', '仮確定'],
]
ws6.update(values=task6_rows, range_name='A44')
print('[6/7] 確定事項一覧: 5件追加 OK')
time.sleep(1)

# ============================================================
# 7. 給与シミュレーションシート 全面書き直し
# ============================================================
ws7 = ss.worksheet('給与シミュレーション')
ws7.clear()

GROSS_LEVELS = [50, 80, 100, 120, 150, 200, 250]
TIER_RATES = {50: 65, 80: 65, 100: 65, 120: 67, 150: 67, 200: 69, 250: 71}
YEAR_BONUS = [0, 1, 2]
AXIS2_BONUS = 1


def calc_payout(gross, year_idx, is_founding=False):
    base = TIER_RATES[gross]
    founding = 4 if is_founding else 0
    rate = min(75 if not is_founding else 80, base + YEAR_BONUS[year_idx] + founding + AXIS2_BONUS)
    return round(gross * rate / 100, 1)


salary_rows = [
    ['月粗利別 手取りシミュレーション  2026-07-02確定  全単位: 万円/月'],
    ['月粗利50〜250万 / 勤続1〜3年目。上限は勤続3年+全社成長で到達。250万超は稀のため省略'],
    [''],
    ['■ 通常メンバー（上限75%）'],
    ['想定: 全社月粗利1,500万（10名体制）→ 軸2=+1%'],
    ['月粗利', '軸1率', '1年目', '2年目', '3年目', '月収上限'],
]

for g in GROSS_LEVELS:
    base = TIER_RATES[g]
    payouts = [f'{calc_payout(g, yi)}万' for yi in range(3)]
    cap = f'{round(g * 0.75, 1)}万'
    salary_rows.append([f'{g}万', f'{base}%'] + payouts + [cap])

salary_rows.extend([
    [''],
    ['■ 創業メンバー（上限80%・軸4プレミアム+4%込み）'],
    ['想定: 10名体制 → 軸2=+1%, 軸4=+4%'],
    ['月粗利', '軸1率', '1年目', '2年目', '3年目', '月収上限'],
])

for g in GROSS_LEVELS:
    base = TIER_RATES[g]
    payouts = [f'{calc_payout(g, yi, is_founding=True)}万' for yi in range(3)]
    cap = f'{round(g * 0.80, 1)}万'
    salary_rows.append([f'{g}万', f'{base}%'] + payouts + [cap])

salary_rows.extend([
    [''],
    ['■ 注記'],
    ['・上限75%/80%は勤続3年+全社成長（軸2+5%）で到達'],
    ['・月粗利250万超は稀（定常97.5万/人が基準）のため表から省略'],
    ['・実際の報酬は4軸構造（個人粗利/全社粗利/勤続/創業）で決定'],
])

ws7.update(values=salary_rows, range_name='A1')
print('[7/7] 給与シミュレーション: 全面書き直し OK')

print('\n=== 全7タスク完了 ===')
print(f'スプレッドシート: https://docs.google.com/spreadsheets/d/{SS_ID}/edit')
