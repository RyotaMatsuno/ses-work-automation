# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8")

# 橋詰・齋藤追加後の実入り再計算
# 橋詰: 4月稼働→6月入金から +15,000(税抜) →松野実入り
# 齋藤: 岡本担当 TERRA請求15,000-岡本払出9,000=松野実入り6,000(税抜) →7月入金から
# ※齋藤5月途中なので7月は日割り分のみ（フル分は8月入金から）

# 税込換算（TERRAは源泉あり）
# 橋詰: 追加TERRA税抜15,000 → 源泉15,000×10.21%=1,531 → 税込16,500-源泉1,531=実入り14,969円
# 齋藤: 追加TERRA税抜15,000 → 源泉1,531 → 松野実入りは岡本払出引後
#        TERRA請求増分15,000税込16,500-源泉1,531=14,969 - 岡本払出9,000×1.1=9,900 = +5,069円/月

hashizume_jissyu = int(15000 * 1.1) - int(15000 * 0.1021)  # = 14,969
saito_terra_jissyu = int(15000 * 1.1) - int(15000 * 0.1021)  # = 14,969
saito_okamoto = int(9000 * 1.1)  # = 9,900
saito_jissyu = saito_terra_jissyu - saito_okamoto  # = 5,069

print("=== 橋詰・齋藤 追加による実入り変化 ===", flush=True)
print(f"橋詰(新) 税抜15,000 → 源泉{int(15000 * 0.1021):,} → 実入り+{hashizume_jissyu:,}円/月", flush=True)
print(f"齋藤よしまさ TERRA+15,000 岡本払出+9,000 → 実入り+{saito_jissyu:,}円/月", flush=True)

print("\n=== 月別実入り（更新後）===", flush=True)

base = {
    "6月": 830123,
    "7月": 882483,
    "8月": 878018,
    "9月": 878018,
}

# 橋詰は4月稼働→6月入金から毎月+14,969
# 齋藤は5月途中稼働→7月入金はフル未満（日割り不明のため7月はゼロ/フルの両パターン表示）
# 8月入金（6月稼働）から毎月フルで+5,069

updated = {
    "6月": base["6月"] + hashizume_jissyu,
    "7月": base["7月"] + hashizume_jissyu,  # 齋藤7月は日割り（別途確認）
    "8月": base["8月"] + hashizume_jissyu + saito_jissyu,
    "9月": base["9月"] + hashizume_jissyu + saito_jissyu,
}

gensen = {
    "6月": 48497 + int(15000 * 0.1021),
    "7月": 48497 + int(15000 * 0.1021),
    "8月": 53602 + int(15000 * 0.1021) * 2,  # 橋詰+齋藤
    "9月": 53602 + int(15000 * 0.1021) * 2,
}

for m in ["6月", "7月", "8月", "9月"]:
    t = updated[m]
    gs = gensen[m]
    g = t + gs
    diff = t - base[m]
    print(f"  {m}入金: 手取り{t:,}円（+{diff:,}）/ 額面{g:,}円", flush=True)

print("\n  ※齋藤の7月は5月途中稼働のため日割り分のみ（稼働開始日が確定次第再計算）", flush=True)
print(f"  ※橋詰の源泉: +{int(15000 * 0.1021):,}円/月 / 齋藤の源泉: +{int(15000 * 0.1021):,}円/月（8月〜）", flush=True)
