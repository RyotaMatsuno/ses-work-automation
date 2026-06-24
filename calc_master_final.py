# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8")

# ============================================================
# 過去チャット全参照による最終確定計算
#
# 【確定前提 - 過去チャット6/1より】
# 1. 源泉 = TERRA税抜 × 10.21%（税込ではなく税抜ベース）
# 2. TERRA税抜請求額（Drive版確定）:
#    - 6月入金(4月稼働): 475,000円（プロパー15名+岡本P3名+森+芹澤+佐々木+小山内）
#    - 7月入金(5月稼働): 475,000円（同構成）
#    - 8月入金(6月稼働): 485,000円（吉田祥平TERRA+40,000、原退場後）
#    - 9月入金(7月稼働): 485,000円（同構成）
#    ※吉田祥平TERRA40,000は8月入金分から別途追加
#
# 3. GL税抜: 毎月108,000円（石崎24,000+山内32,000+荒井32,000 → 各木原控除後）
#    - 石崎: サイト30日 → work_m+1で入金
#    - 山内・荒井: サイト45日 → work_m+2で入金
#    ※石崎(30日)は5月稼働→6月入金、6月稼働→7月入金… でずれる
#    但し過去チャットでは毎月108,000円で一括計算しているので同方式を採用
#
# 4. FT税抜（Drive版月別確定値）:
#    - 6月入金(4月稼働): 371,600(45日分)+20,400(田中みさ55日分)=392,000
#    - 7月入金(5月稼働): 419,200(45日分)+20,400(田中55日分)=439,600
#      ※7月は原昌志5月稼働含む・鶴川5月稼働含む（確認: 鶴川は6月入場→7月は未含む）
#    - 8月入金(6月稼働): 375,200(45日分)+20,400(田中55日分)=395,600
#      ※原昌志退場・鶴川6月入場は8月から含む→但し鶴川は岡本全額払出で実入り0
#    - 9月入金(7月稼働): 395,600（8月と同構成）+ 遠藤健太追加
#    ※吉田祥平FT24,000は8月入金から別途追加
#
# 5. 岡本払出税抜（月別）:
#    - 6月: TERRA3名27,000+佐々木20,000+橋本23,800 = 70,800
#    - 7月: 70,800 + 鶴見50,000 = 120,800
#    - 8月以降: 120,800 + 鶴川47,600 = 168,400
#    - 9月以降(遠藤追加): 168,400 + 遠藤17,000 = 185,400
#
# 6. 木原分（税込）:
#    - 6月・7月: 116,000円（原昌志含む）
#    - 8月以降: 96,000円（原昌志退場後）
#
# 7. 鶴見（直契約）:
#    - 6月稼働→7月末入金: 100,000-50,000=50,000税抜 → 税込55,000（7月から）
#
# 8. 吉田祥平: 6月入場
#    - TERRA分: 税抜40,000 → 8月入金から（源泉対象）
#    - FT分: 税抜24,000 → 8月入金から（源泉なし）
#
# 9. 遠藤健太: 7月入場
#    - FT岡本折半: 松野実入り税抜17,000 → 9月入金から
#    - 岡本払出: 税抜17,000 → 9月から
# ============================================================


def calc_month(
    label,
    terra_zeinuki_base,
    gl_zeinuki,
    ft_zeinuki_base,
    okamoto_zeinuki,
    kihara,
    extra_terra=0,
    extra_ft=0,
    extra_choku=0,
):
    """
    extra_terra: TERRA追加分（税抜、源泉対象）
    extra_ft:    FT追加分（税抜、源泉なし）
    extra_choku: 直契約追加分（税込）
    """
    # TERRA
    total_terra_zeinuki = terra_zeinuki_base + extra_terra
    terra_gensen = int(total_terra_zeinuki * 0.1021)
    terra_jissyu = int(total_terra_zeinuki * 1.1) - terra_gensen

    # GL
    gl_zeikomi = int(gl_zeinuki * 1.1)

    # FT
    total_ft_zeinuki = ft_zeinuki_base + extra_ft
    ft_zeikomi = int(total_ft_zeinuki * 1.1)

    # 岡本払出・木原
    okamoto_zeikomi = int(okamoto_zeinuki * 1.1)

    # 合計
    tedori = terra_jissyu + gl_zeikomi + ft_zeikomi + extra_choku - okamoto_zeikomi - kihara
    gengaku = tedori + terra_gensen

    return {
        "label": label,
        "terra_zeinuki": total_terra_zeinuki,
        "terra_gensen": terra_gensen,
        "terra_jissyu": terra_jissyu,
        "gl_zeikomi": gl_zeikomi,
        "ft_zeikomi": ft_zeikomi,
        "extra_choku": extra_choku,
        "okamoto_zeikomi": okamoto_zeikomi,
        "kihara": kihara,
        "tedori": tedori,
        "gengaku": gengaku,
    }


def print_detail(r, notes):
    print(f"\n{'=' * 65}", flush=True)
    print(f"◆ {r['label']}", flush=True)
    print(f"{'=' * 65}", flush=True)
    print(f"  [TERRA]    税抜{r['terra_zeinuki']:,}円 × 1.1 = 税込{int(r['terra_zeinuki'] * 1.1):,}円", flush=True)
    print(f"             源泉{r['terra_gensen']:,}円 (×10.21%) → 実入り{r['terra_jissyu']:,}円", flush=True)
    print(f"  [GL]       税抜{int(r['gl_zeikomi'] / 1.1):,}円 × 1.1 = 税込{r['gl_zeikomi']:,}円", flush=True)
    print(f"  [FT]       税抜{int(r['ft_zeikomi'] / 1.1):,}円 × 1.1 = 税込{r['ft_zeikomi']:,}円", flush=True)
    if r["extra_choku"]:
        print(f"  [直契約]   税込{r['extra_choku']:,}円", flush=True)
    print(f"  [岡本払出] 税抜{int(r['okamoto_zeikomi'] / 1.1):,}円 × 1.1 = △{r['okamoto_zeikomi']:,}円", flush=True)
    print(f"  [木原分]   △{r['kihara']:,}円（税込）", flush=True)
    for n in notes:
        print(f"  ※ {n}", flush=True)
    print(f"  {'─' * 50}", flush=True)
    print(
        f"  計算: {r['terra_jissyu']:,}+{r['gl_zeikomi']:,}+{r['ft_zeikomi']:,}+{r['extra_choku']:,}-{r['okamoto_zeikomi']:,}-{r['kihara']:,}",
        flush=True,
    )
    print(f"  ★手取り: {r['tedori']:,}円", flush=True)
    print(f"  TERRA源泉: +{r['terra_gensen']:,}円（確申還付）", flush=True)
    print(f"  ★額面:    {r['gengaku']:,}円", flush=True)


# ---- 6月入金（4月稼働）----
r6 = calc_month(
    "6月入金（4月稼働）",
    terra_zeinuki_base=475000,
    gl_zeinuki=108000,
    ft_zeinuki_base=392000,  # 371,600+20,400
    okamoto_zeinuki=70800,  # TERRA3名+佐々木+橋本
    kihara=116000,
)
print_detail(
    r6,
    [
        "FT: 笠井68,000+木村47,600+加藤38,400+川崎27,200+立野47,600+佐々木駿7,200+橋本47,600=371,600 +田中20,400",
        "岡本払出: 天野9,000+岩瀬9,000+加藤T9,000+佐々木20,000+橋本23,800=70,800",
        "鶴川は6月入場のため含まず、吉田は6月入場のため含まず",
    ],
)

# ---- 7月入金（5月稼働＋鶴見6月→7月末）----
# FT7月: 鶴川は6月入場なので5月稼働分には含まれない→Drive版439,600
# 鶴見初回: 6月稼働→7月末 手取50,000税抜→税込55,000
r7 = calc_month(
    "7月入金（5月稼働＋鶴見初回）",
    terra_zeinuki_base=475000,
    gl_zeinuki=108000,
    ft_zeinuki_base=439600,  # Drive版（原昌志5月稼働含む）
    okamoto_zeinuki=120800,  # 70,800+鶴見50,000
    kihara=116000,  # 原昌志5月末まで→木原116,000
    extra_choku=55000,  # 鶴見税込
)
print_detail(
    r7,
    [
        "FT: 6月基準395,600 + 原昌志5月まで含む+43,600? → Drive版439,600採用",
        "鶴川は6月入場→5月稼働分に含まず",
        "鶴見: 税抜100,000-岡本払50,000=50,000×1.1=55,000円を直接加算",
        "岡本払出: 70,800+鶴見50,000=120,800税抜",
        "木原: 原昌志は5月末退場のため5月稼働分には含む→116,000",
    ],
)

# ---- 8月入金（6月稼働）----
# 吉田TERRA(40,000税抜)・吉田FT(24,000税抜)追加
# 鶴川6月入場→FT請求47,600発生するが岡本全額払出→実入り0
# Drive版FT395,600（原退場・鶴川含む）
# 鶴川のFT請求47,600はDrive版395,600に含まれているが岡本払出でゼロになる
r8 = calc_month(
    "8月入金（6月稼働）",
    terra_zeinuki_base=485000,  # Drive版（原退場後）
    gl_zeinuki=108000,
    ft_zeinuki_base=395600,  # Drive版（原退場後・鶴川含む）
    okamoto_zeinuki=168400,  # 70,800+鶴川47,600+鶴見50,000
    kihara=96000,  # 原退場後
    extra_terra=40000,  # 吉田TERRA（源泉対象）
    extra_ft=24000,  # 吉田FT
    extra_choku=55000,  # 鶴見
)
print_detail(
    r8,
    [
        "吉田TERRA: 粗利5万×80%=40,000税抜（源泉対象）",
        "吉田FT: 粗利5万×48%(小坂折半)=24,000税抜",
        "鶴川: FT請求47,600はDrive版395,600に含む→岡本払出168,400に47,600込み",
        "岡本払出: 70,800+鶴川47,600+鶴見50,000=168,400税抜",
        "木原: 原退場後→96,000",
    ],
)

# ---- 9月入金（7月稼働）----
# 遠藤健太追加: FT松野実入り17,000税抜・岡本払出+17,000税抜
r9 = calc_month(
    "9月入金（7月稼働）",
    terra_zeinuki_base=485000,
    gl_zeinuki=108000,
    ft_zeinuki_base=395600,  # 8月と同構成
    okamoto_zeinuki=185400,  # 168,400+遠藤17,000
    kihara=96000,
    extra_terra=40000,  # 吉田TERRA
    extra_ft=24000 + 17000,  # 吉田FT+遠藤FT
    extra_choku=55000,  # 鶴見
)
print_detail(
    r9,
    [
        "遠藤健太: FT岡本折半 粗利5万×68%÷2=17,000税抜（松野実入り）",
        "岡本払出: 168,400+遠藤17,000=185,400税抜",
        "吉田TERRA・吉田FT・鶴見は8月と同じ",
    ],
)

# ---- サマリー ----
print(f"\n{'=' * 65}", flush=True)
print("【最終サマリー（全前提込み）】", flush=True)
print(f"{'=' * 65}", flush=True)
print(f"{'月':<14}{'手取り(税込)':>14}{'TERRA源泉':>12}{'額面':>13}", flush=True)
print(f"{'─' * 55}", flush=True)

rows = [r6, r7, r8, r9]
labels = ["6月入金", "7月入金", "8月入金", "9月入金"]
prev = None
for r, lbl in zip(rows, labels):
    diff = f"  ({r['tedori'] - prev:+,})" if prev is not None else ""
    print(f"{lbl:<14}{r['tedori']:>13,}円{r['terra_gensen']:>10,}円{r['gengaku']:>12,}円{diff}", flush=True)
    prev = r["tedori"]

print("\n【照合チェック】", flush=True)
print(f"  6月 過去チャット確定値: 830,122円  今回: {r6['tedori']:,}円  差: {r6['tedori'] - 830122:+,}円", flush=True)
print(f"  7月 過去チャット確定値: 937,482円  今回: {r7['tedori']:,}円  差: {r7['tedori'] - 937482:+,}円", flush=True)
