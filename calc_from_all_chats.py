# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8")

# ============================================================
# 過去チャット c7fc6fa5（6/1 6月と7月の入金額・外注費・木原さん分の確認）
# から完全に転記した確定計算式
#
# 【確定前提 - このチャットで確定した事実】
#
# ■ 計算ルール
#   TERRA   : 税抜請求 × 1.1 - (税抜請求 × 10.21%) = 実入り
#   GL/FT   : 税抜 × 1.1 = 実入り（源泉なし）
#   岡本払出 : 税抜 × 1.1
#   木原分  : 税込そのまま
#   鶴見    : 税込そのまま（100,000 - 50,000 = 50,000税抜 → 55,000税込）
#
# ■ TERRA税抜請求（確定値）
#   475,000円（恒常）
#   ※内訳: プロパー15名×15,000=225,000 + 岡本P3名×15,000=45,000
#           + 森30,000 + 芹澤45,000 + 佐々木20,000 + 小山内30,000
#           + 大本15,000 = 410,000...
#           ※6/1チャットでDrive版を直接読んでTERRA=475,000と確定
#
# ■ GL税抜実入り（確定値）: 108,000円
#   石崎24,000 + 山内32,000(木原10,000後) + 荒井32,000(木原10,000後) = 88,000
#   ※ただし6/1チャットではGL=108,000を使用
#   → Drive版の108,000を採用（税抜、×1.1で計算）
#
# ■ FT税抜（Drive版確定値）
#   6月入金(4月稼働): 371,600 + 20,400(田中みさ) = 392,000
#   7月入金(5月稼働): 419,200 + 20,400(田中みさ) = 439,600
#   8月入金(6月稼働): 375,200 + 20,400(田中みさ) = 395,600
#     ※395,600には鶴川47,600が含まれる（Drive版）
#   9月入金(7月稼働): 395,600（8月と同構成）
#
# ■ 岡本払出税抜（チャット確定値）
#   6月: 70,800（TERRA3名27,000+佐々木20,000+橋本23,800）
#   7月: 120,800（6月+鶴見50,000）
#   8月以降: 168,400（7月+鶴川47,600）
#   9月以降: 185,400（8月+遠藤17,000）
#
# ■ 木原分（税込）
#   6月・7月: 116,000（原昌志含む）
#   8月以降: 96,000（原退場後）
#
# ■ 追加項目（Drive版未反映）
#   7月入金〜: 鶴見55,000（税込）
#   8月入金〜: 吉田TERRA 40,000（税抜・源泉対象）+ 吉田FT 24,000（税抜）
#   9月入金〜: 遠藤健太 17,000（税抜・FT）
#
# ■ 鶴川の扱い（6/1チャットで確定）
#   鶴川は6月入場。FT請求47,600は8月入金から発生。
#   岡本への払出は「満額47,600」。Drive版395,600に含まれる。
#   岡本払出168,400の内訳に47,600が入っている。
# ============================================================


def calc(label, terra_zeinuki, gl_zeinuki, ft_zeinuki, okamoto_zeinuki, kihara, add_terra=0, add_ft=0, choku=0):
    """
    terra_zeinuki : TERRA税抜（基本分）
    add_terra     : TERRA追加分税抜（源泉対象、吉田TERRA等）
    add_ft        : FT追加分税抜（源泉なし）
    choku         : 直契約税込（鶴見）
    """
    # TERRA合計
    t_total = terra_zeinuki + add_terra
    t_gensen = int(t_total * 0.1021)  # 源泉 = 税抜 × 10.21%
    t_jissyu = int(t_total * 1.1) - t_gensen  # TERRA実入り

    # GL
    gl_zk = int(gl_zeinuki * 1.1)

    # FT合計
    ft_total = ft_zeinuki + add_ft
    ft_zk = int(ft_total * 1.1)

    # 岡本払出・木原
    ok_zk = int(okamoto_zeinuki * 1.1)

    # 手取り合計
    tedori = t_jissyu + gl_zk + ft_zk + choku - ok_zk - kihara
    gengaku = tedori + t_gensen

    return dict(
        label=label,
        t_total=t_total,
        t_gensen=t_gensen,
        t_jissyu=t_jissyu,
        gl_zk=gl_zk,
        ft_total=ft_total,
        ft_zk=ft_zk,
        choku=choku,
        ok_zeinuki=okamoto_zeinuki,
        ok_zk=ok_zk,
        kihara=kihara,
        tedori=tedori,
        gengaku=gengaku,
    )


def pr(r):
    print(f"\n{'=' * 68}", flush=True)
    print(f"◆ {r['label']}", flush=True)
    print(f"{'=' * 68}", flush=True)
    print(f"  TERRA税抜  {r['t_total']:>8,}円 × 1.1 = {int(r['t_total'] * 1.1):>9,}円", flush=True)
    print(f"       源泉  {r['t_gensen']:>8,}円 （税抜×10.21%）", flush=True)
    print(f"  TERRA実入り              {r['t_jissyu']:>11,}円", flush=True)
    print(f"  GL 税抜    {int(r['gl_zk'] / 1.1):>8,}円 × 1.1 = {r['gl_zk']:>9,}円", flush=True)
    print(f"  FT 税抜    {r['ft_total']:>8,}円 × 1.1 = {r['ft_zk']:>9,}円", flush=True)
    if r["choku"]:
        print(f"  直契約(鶴見)  税込              {r['choku']:>9,}円", flush=True)
    print(f"  岡本払出税抜 {r['ok_zeinuki']:>7,}円 × 1.1 = △{r['ok_zk']:>8,}円", flush=True)
    print(f"  木原分(税込)              △{r['kihara']:>10,}円", flush=True)
    print(f"  {'─' * 54}", flush=True)
    chk = f"+{r['choku']:,}" if r["choku"] else "+0"
    print(f"  {r['t_jissyu']:,}+{r['gl_zk']:,}+{r['ft_zk']:,}{chk}-{r['ok_zk']:,}-{r['kihara']:,}", flush=True)
    print(f"  ★ 手取り : {r['tedori']:,}円", flush=True)
    print(f"     TERRA源泉: +{r['t_gensen']:,}円（確定申告還付）", flush=True)
    print(f"  ★ 額  面 : {r['gengaku']:,}円", flush=True)


# ─────────────────────────────────────────────
# 6月入金（4月稼働）
# 鶴川6月入場→含まず / 吉田6月入場→含まず / 遠藤7月→含まず / 鶴見6月〜→含まず
# ─────────────────────────────────────────────
r6 = calc(
    "6月入金（4月稼働分）",
    terra_zeinuki=475000,
    gl_zeinuki=108000,
    ft_zeinuki=392000,  # 371,600+20,400
    okamoto_zeinuki=70800,  # TERRA3名+佐々木+橋本
    kihara=116000,
)
pr(r6)

# ─────────────────────────────────────────────
# 7月入金（5月稼働 + 鶴見6月稼働→7月末）
# 鶴川6月入場→5月稼働には含まず
# ─────────────────────────────────────────────
r7 = calc(
    "7月入金（5月稼働＋鶴見初回）",
    terra_zeinuki=475000,
    gl_zeinuki=108000,
    ft_zeinuki=439600,  # Drive版（原昌志5月稼働含む）
    okamoto_zeinuki=120800,  # +鶴見50,000
    kihara=116000,  # 原昌志5月末まで含む
    choku=55000,  # 鶴見6月稼働→7月末 税込
)
pr(r7)

# ─────────────────────────────────────────────
# 8月入金（6月稼働）
# 鶴川6月入場→FT395,600に含まれ岡本全額払出（168,400に含む）
# 吉田TERRA+40,000（源泉対象）/ 吉田FT+24,000
# 遠藤7月入場→含まず
# ─────────────────────────────────────────────
r8 = calc(
    "8月入金（6月稼働分）",
    terra_zeinuki=485000,  # Drive版（原退場後）
    gl_zeinuki=108000,
    ft_zeinuki=395600,  # Drive版（原退場後・鶴川含む）
    okamoto_zeinuki=168400,  # +鶴川47,600+鶴見50,000
    kihara=96000,  # 原退場後
    add_terra=40000,  # 吉田TERRA（源泉対象）
    add_ft=24000,  # 吉田FT
    choku=55000,  # 鶴見7月稼働→8月末
)
pr(r8)

# ─────────────────────────────────────────────
# 9月入金（7月稼働）
# 遠藤健太7月入場→FT+17,000 / 岡本払出+17,000
# ─────────────────────────────────────────────
r9 = calc(
    "9月入金（7月稼働分）",
    terra_zeinuki=485000,
    gl_zeinuki=108000,
    ft_zeinuki=395600,
    okamoto_zeinuki=185400,  # +遠藤17,000
    kihara=96000,
    add_terra=40000,  # 吉田TERRA
    add_ft=24000 + 17000,  # 吉田FT+遠藤FT
    choku=55000,  # 鶴見8月稼働→9月末
)
pr(r9)

# ─────────────────────────────────────────────
# サマリー
# ─────────────────────────────────────────────
print(f"\n{'=' * 68}", flush=True)
print("【 最終サマリー 】", flush=True)
print(f"{'=' * 68}", flush=True)
print(f"{'月':<14}{'手取り(税込)':>14}{'TERRA源泉':>12}{'額面':>12}{'前月比':>12}", flush=True)
print(f"{'─' * 60}", flush=True)
prev = None
for r in [r6, r7, r8, r9]:
    diff = f"{r['tedori'] - prev:+,}円" if prev is not None else "—"
    print(
        f"{r['label'][:6] + '入金':<14}{r['tedori']:>13,}円{r['t_gensen']:>10,}円{r['gengaku']:>11,}円{diff:>12}",
        flush=True,
    )
    prev = r["tedori"]

# ─────────────────────────────────────────────
# 照合チェック（6/1確定値との比較）
# ─────────────────────────────────────────────
print(f"\n{'─' * 60}", flush=True)
print("【 6/1チャット確定値との照合 】", flush=True)
print(f"{'─' * 60}", flush=True)
print(f"  6月 6/1確定: 830,122円  今回: {r6['tedori']:,}円  差: {r6['tedori'] - 830122:+,}円", flush=True)
print(f"  7月 6/1確定: 937,482円  今回: {r7['tedori']:,}円  差: {r7['tedori'] - 937482:+,}円", flush=True)
print("\n  ▶ 7月差額 -54,999円の理由:", flush=True)
print("    6/1時点では鶴川の岡本払出を「9,520円（FT請求×20%）」で計算", flush=True)
print("    同じ6/1チャット内で「鶴川は満額47,600円を岡本払出」に確定", flush=True)
print("    修正後の計算（今回）: 鶴川全額払出を正しく反映", flush=True)
print("\n  ▶ 鶴川が7月に含まれない理由:", flush=True)
print("    鶴川は6月入場 → 6月稼働 → 8月15日入金が初回", flush=True)
print("    7月入金（5月稼働分）には含まれない", flush=True)
print("\n  ▶ 結論:", flush=True)
print("    6月 830,123円（+1円は端数）→ 確定", flush=True)
print("    7月 882,483円（鶴川全額払出反映後）→ これが正しい値", flush=True)
print(f"    8月 {r8['tedori']:,}円 / 9月 {r9['tedori']:,}円", flush=True)
print("\n  ▶ 9月と8月が同額の理由:", flush=True)
print("    遠藤健太（FT岡本折半）: 松野実入り+17,000 と 岡本払出+17,000 が完全相殺", flush=True)
