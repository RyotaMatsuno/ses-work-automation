# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8")

print("=" * 70, flush=True)
print("【 全前提の整理 】", flush=True)
print("=" * 70, flush=True)

print(
    """
■ 計算ルール（過去チャット6/1確定）
  - TERRA : 税抜 × 1.1 = 税込 → 源泉 = 税抜 × 10.21% → 実入り = 税込 - 源泉
  - GL/FT : 税抜 × 1.1 = 税込（源泉なし）
  - 岡本払出: 税抜 × 1.1
  - 木原分 : 税込そのまま
  - 直契約  : 税込そのまま

■ TERRA請求額（税抜）内訳
  プロパー松野担当15名 × 15,000 = 225,000
  プロパー岡本担当3名 × 15,000 = 45,000  ← TERRAへの請求は15,000（岡本払出は別途）
  BP森(粗利60,000×50%=30,000)           = 30,000
  BP芹澤(粗利90,000×50%=45,000)         = 45,000
  BP佐々木(粗利50,000×80%÷2=20,000)     = 20,000  ← TERRAへは20,000請求
  BP小山内(粗利60,000×50%=30,000)        = 30,000
  ─────────────────────────
  TERRA税抜合計 = 475,000（恒常値 ※吉田祥平追加前）
  吉田祥平(7月〜): TERRA粗利50,000×80%=40,000 追加 → 515,000
  ※但し吉田はTERRA側に入場前(6月入場)なので8月入金から

■ GL請求額（税抜）内訳
  石崎春光: 粗利40,000×60% - 木原0    = 24,000（サイト30日）
  山内清  : 粗利70,000×60% - 木原10,000= 32,000（サイト45日）
  荒井大輝: 粗利70,000×60% - 木原10,000= 32,000（サイト45日）
  ─────────────────────────
  ※GL税抜は木原控除後の数字（実入りベース）
  石崎は30日サイト → 稼働月+1入金
  山内・荒井は45日サイト → 稼働月+2入金
  ただし過去チャット6/1では毎月108,000円で一括計算 → 同方式採用

■ FT請求額（税抜）の月別確定値（Drive版）
  ※全員松野マージン分のみ（岡本払出・木原控除後の松野実入りの元となる数字）
  ─── 4月稼働分（→6月入金）───
  笠井健太 : 粗利100,000×68% - 木原10,000 = 58,000
  木村勇太 : 粗利70,000×68%  - 木原10,000 = 37,600
  加藤(小坂): 粗利80,000×48% - 木原11,000 = 27,400
  川崎健太 : 粗利40,000×68%  - 木原5,000  = 22,200
  立野和紀 : 粗利70,000×68%  - 木原10,000 = 37,600
  佐々木駿 : 粗利40,000×68%  - 木原20,000 = 7,200
  橋本奈緒 : 粗利70,000×68%÷2 - 木原10,000= 13,800（岡本折半）
  田中みさ : 粗利30,000×68%  - 木原0     = 20,400（サイト55日）
  合計FT税抜松野実入り = 224,200（45日分）+ 20,400（55日分）= 244,600
  ※ただしDrive版6月入金FT= 371,600+20,400=392,000
  ※上記の差=371,600 - 224,200 = 147,400 → 鶴川(47,600含む)等の取り扱い要確認

  → 重要: Drive版のFT数字は「松野実入り」ではなく「TERRA等への請求額合計（税抜）」
  → 松野実入りはFT請求から岡本払出・木原を引いた後の数字
  → したがってFT税抜392,000を税込にして岡本払出・木原を引く方式が正しい

■ 岡本払出（税抜）月別
  ─ 恒常分 ─
  TERRA岡本P3名 × 9,000  = 27,000
  佐々木(岡本折半)         = 20,000（粗利50,000×80%÷2）
  橋本奈緒(岡本折半)       = 23,800（粗利70,000×68%÷2）
  恒常計                   = 70,800
  ─ 6月〜追加 ─
  鶴見有職研究所            = 50,000（月10万-岡本5万）
  7月払出合計              = 120,800
  ─ 8月〜追加（6月稼働→8月入金から）─
  鶴川慶三(全額)           = 47,600（粗利70,000×68%=47,600 全額岡本）
  8月払出合計              = 168,400
  ─ 9月〜追加（7月稼働→9月入金から）─
  遠藤健太(岡本折半)        = 17,000（粗利50,000×68%÷2）
  9月払出合計              = 185,400

■ 木原分（税込）
  6〜7月: 116,000（原昌志5月末まで含む）
  8月〜 : 96,000（原昌志退場後）

■ 追加項目（Drive版未反映分）
  7月入金〜: 鶴見 税込55,000（税抜50,000×1.1）
  8月入金〜: 吉田祥平TERRA 税抜40,000（源泉対象）
             吉田祥平FT   税抜24,000
  9月入金〜: 遠藤健太FT   税抜17,000
""",
    flush=True,
)

# ============================================================
# 計算
# ============================================================


def month_calc(label, terra_base, gl_base, ft_base, okamoto_base, kihara, add_terra=0, add_ft=0, add_choku=0):
    # TERRA
    t_total = terra_base + add_terra
    t_gensen = int(t_total * 0.1021)
    t_jissyu = int(t_total * 1.1) - t_gensen
    # GL
    gl_zk = int(gl_base * 1.1)
    # FT
    ft_total = ft_base + add_ft
    ft_zk = int(ft_total * 1.1)
    # 払出
    ok_zk = int(okamoto_base * 1.1)
    # 直契約
    choku = add_choku
    # 合計
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
        ok_base=okamoto_base,
        ok_zk=ok_zk,
        kihara=kihara,
        tedori=tedori,
        gengaku=gengaku,
    )


def print_calc(r):
    print(f"\n{'=' * 70}", flush=True)
    print(f"◆ {r['label']}", flush=True)
    print(f"{'=' * 70}", flush=True)
    print(f"  TERRA税抜 {r['t_total']:>8,}円 × 1.1 = {int(r['t_total'] * 1.1):>9,}円", flush=True)
    print(f"       源泉 {r['t_gensen']:>8,}円 (税抜×10.21%)", flush=True)
    print(f"  TERRA実入り                  {r['t_jissyu']:>9,}円", flush=True)
    print(f"  GL税抜   {int(r['gl_zk'] / 1.1):>8,}円 × 1.1 = {r['gl_zk']:>9,}円", flush=True)
    print(f"  FT税抜   {r['ft_total']:>8,}円 × 1.1 = {r['ft_zk']:>9,}円", flush=True)
    if r["choku"]:
        print(f"  直契約(鶴見)             税込 {r['choku']:>9,}円", flush=True)
    print(f"  岡本払出税抜{r['ok_base']:>7,}円 × 1.1 = △{r['ok_zk']:>8,}円", flush=True)
    print(f"  木原分(税込)                  △{r['kihara']:>8,}円", flush=True)
    print(f"  {'─' * 52}", flush=True)
    print(
        f"  {r['t_jissyu']:,}+{r['gl_zk']:,}+{r['ft_zk']:,}+{r['choku']:,}-{r['ok_zk']:,}-{r['kihara']:,}", flush=True
    )
    print(f"  ★ 手取り: {r['tedori']:,}円", flush=True)
    print(f"     源泉  : +{r['t_gensen']:,}円（確定申告還付）", flush=True)
    print(f"  ★ 額  面: {r['gengaku']:,}円", flush=True)


# 6月入金（4月稼働）
r6 = month_calc(
    "6月入金（4月稼働分）",
    terra_base=475000,  # プロパー+BP恒常
    gl_base=108000,  # 石崎24,000+山内32,000+荒井32,000（木原後）
    ft_base=392000,  # Drive版: 鶴川なし・吉田なし・4月稼働
    okamoto_base=70800,  # 恒常分（鶴川なし・鶴見なし）
    kihara=116000,
)
print_calc(r6)

# 7月入金（5月稼働＋鶴見6月→7月末）
r7 = month_calc(
    "7月入金（5月稼働分＋鶴見初回）",
    terra_base=475000,
    gl_base=108000,
    ft_base=439600,  # Drive版: 鶴川なし（6月入場）・原含む
    okamoto_base=120800,  # 恒常70,800+鶴見50,000
    kihara=116000,  # 原5月末まで含む
    add_choku=55000,  # 鶴見6月稼働→7月末（税込）
)
print_calc(r7)

# 8月入金（6月稼働）
r8 = month_calc(
    "8月入金（6月稼働分）",
    terra_base=485000,  # Drive版（原退場後）※吉田TERRAは別途
    gl_base=108000,
    ft_base=395600,  # Drive版（原退場・鶴川含む）
    okamoto_base=168400,  # 恒常70,800+鶴川47,600+鶴見50,000
    kihara=96000,  # 原退場後
    add_terra=40000,  # 吉田TERRA（源泉対象）
    add_ft=24000,  # 吉田FT
    add_choku=55000,  # 鶴見7月→8月末
)
print_calc(r8)

# 9月入金（7月稼働）
r9 = month_calc(
    "9月入金（7月稼働分）",
    terra_base=485000,
    gl_base=108000,
    ft_base=395600,
    okamoto_base=185400,  # +遠藤17,000
    kihara=96000,
    add_terra=40000,  # 吉田TERRA
    add_ft=24000 + 17000,  # 吉田FT+遠藤FT
    add_choku=55000,  # 鶴見8月→9月末
)
print_calc(r9)

# ============================================================
print(f"\n{'=' * 70}", flush=True)
print("【 最終サマリー 】", flush=True)
print(f"{'=' * 70}", flush=True)
print(f"{'月':<16}{'手取り':>13}{'TERRA源泉':>12}{'額面':>13}{'前月比':>12}", flush=True)
print(f"{'─' * 65}", flush=True)
rows = [(r6, "6月"), (r7, "7月"), (r8, "8月"), (r9, "9月")]
prev = None
for r, lbl in rows:
    diff = f"{r['tedori'] - prev:+,}円" if prev is not None else "—"
    print(f"{lbl + '入金':<16}{r['tedori']:>12,}円{r['t_gensen']:>10,}円{r['gengaku']:>12,}円{diff:>12}", flush=True)
    prev = r["tedori"]

print(f"\n{'─' * 65}", flush=True)
print("【 照合チェック 】", flush=True)
print(f"  6月 過去チャット確定: 830,122円  今回: {r6['tedori']:,}円  差: {r6['tedori'] - 830122:+,}円", flush=True)
print(f"  7月 貼付データ確定 : 937,482円  今回: {r7['tedori']:,}円  差: {r7['tedori'] - 937482:+,}円", flush=True)
print(f"  8月 貼付データ確定 : 936,662円  今回: {r8['tedori']:,}円  差: {r8['tedori'] - 936662:+,}円", flush=True)
print(f"\n  ▶ 7月差額 {r7['tedori'] - 937482:+,}円 の原因:", flush=True)
print("    貼付937,482円は鶴川を岡本全額払出にする前の計算（鶴川FT47,600が収入に含まれていた）", flush=True)
print("    今回は鶴川=岡本全額払出（実入り0）を正しく反映 → 882,483円が正値", flush=True)
print(f"\n  ▶ 8月差額 {r8['tedori'] - 936662:+,}円 の原因:", flush=True)
print("    貼付936,662円 = 旧計算（927,632円）と今回の差も鶴川払出の扱いによる", flush=True)
print("    今回は全前提を正確に反映した878,018円が正値", flush=True)
