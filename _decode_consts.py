import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 定数の実際の値をデコードして確認
vals = {
    "VAL_RECRUITING": "e58b9fe99b86e4b8ad",
    "VAL_ACTIVE2": "e7a8bce5838de58fafe883bd",
    "VAL_ADJUSTING": "e8aabfe695b4e4b8ad",
    "PROP_WORKST": "e7a8bce5838de78ab6e6b381",
    "PROP_STA": "e69c80e5af84e3828ae9a785",
    "PROP_INI": "e382a4e3838be382b7e383a3e383ab",
    "PROP_NAME": "e5908de5898d",
    "PROP_STATUS": "e382b9e38386e383bce382bfe382b9",
}
for k, v in vals.items():
    print(f"{k} = '{bytes.fromhex(v).decode()}'")

print()
# engineer_queryはPROP_WORKSTフィルタがない！
# project_queryにはある: _select_prop(eng, PROP_WORKST) not in (VAL_ACTIVE2, VAL_ADJUSTING)
# engineer_queryには稼働状況フィルタが存在しない → 全エンジニアが対象になっている？
print("★ engineer_query には PROP_WORKST フィルタがない（project_queryにはある）")
print("→ 稼働不可・離脱済みエンジニアも含めてマッチングしている可能性")

# 案件フィルタも確認: PROP_RATEでフィルタしているのはどういう意味？
print()
print("案件取得フィルタ: PROP_RATE > 0")
print("→ 単価が設定されている案件のみ対象（これは正しい）")
