# -*- coding: utf-8 -*-
# LINE公式アカウントの料金プランを調査用メモ
# 2026年6月時点の公式料金（記憶ベース、要確認）

plans = [
    {
        "name": "フリープラン",
        "monthly": 0,
        "free_push": 200,
        "additional": "不可",
    },
    {
        "name": "ライトプラン",
        "monthly": 5000,
        "free_push": 5000,
        "additional": "不可",
    },
    {
        "name": "スタンダードプラン",
        "monthly": 15000,
        "free_push": 30000,
        "additional": "3円/通",
    },
]

for p in plans:
    print(f"【{p['name']}】月額: {p['monthly']}円 / 無料Push: {p['free_push']}通 / 追加: {p['additional']}", flush=True)

print("\n現在: フリープラン（月200通）", flush=True)
print("照会1回=1通消費想定での必要通数試算:", flush=True)
for times in [50, 100, 200, 500]:
    print(f"  月{times}回照会 → {times}通消費", flush=True)
