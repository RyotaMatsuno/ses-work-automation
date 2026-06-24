import io
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

print("=" * 70)
print("静的バグ解析 - line_query.py 全問題点を列挙")
print("=" * 70)

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

issues = []

# ================================================================
# BUG-1: format_project_result で _text_prop(engineer, "イニシャル") をハードコード
# ================================================================
if '_text_prop(engineer, "イニシャル")' in src:
    issues.append("BUG-1: format_project_result がイニシャルを直接文字列で引いている（PROP_INI定数を使うべき）")

# ================================================================
# BUG-2: format_project_result で _text_prop(engineer, "最寄り駅") をハードコード
# ================================================================
if '_text_prop(engineer, "最寄り駅")' in src:
    issues.append("BUG-2: format_project_result が最寄り駅を直接文字列で引いている（PROP_STA定数を使うべき）")

# ================================================================
# BUG-3: project_query で日本語直書き ("案件名","ステータス","必要スキル","担当者")
# ================================================================
for literal in ['"案件名"', '"ステータス"', '"必要スキル"', '"担当者"', '"稼働状況"', '"スキル"', '"単価（万円）"']:
    if literal in src:
        issues.append(f"BUG-3: project_query/format_engineer_result が {literal} を直書き（定数を使うべき）")

# ================================================================
# BUG-4: engineer_query の matched_engineers が空でも stations チェックが甘い
# ================================================================
# _match_station: sta が空 + memo に駅名なし → True を返す（正しい仕様なので問題なし）

# ================================================================
# BUG-5: _limit_reply が新フォーマット（①で始まらない）で打ち切れない
# ================================================================
# 新フォーマット: "① 案件名\n  必須: ...\n  単価: ...\n  場所..."
# _limit_reply は line.startswith(f"{_num_label(TOP_LIMIT + 1)}") で ⑥ を探す
# 新フォーマットは "⑥ 案件名" で始まるので startswith("⑥") で正しく打ち切れる → OK

# ================================================================
# BUG-6: handle_line_query の 100文字ガード
# ================================================================
# 「HS 北小金」= 6文字 → OK
# 「HS 北小金（詳細を教えてください）」= 17文字 → OK (100未満なのでクエリとして処理)
# しかし「HS 北小金 詳細スキルはJavaとSpringで経験年数は10年以上...」= 50文字前後 → 誤分類リスク

# ================================================================
# BUG-7: classify_query で駅名に空白が含まれると以降を切り捨てる
# ================================================================
test_sta = re.match(r"^([A-Za-z.]{1,8})[\s\u3000/]+(.+)$", "HS 西新宿五丁目")
if test_sta:
    print(f"INFO: 'HS 西新宿五丁目' → initial={test_sta.group(1)}, station={test_sta.group(2)}")

# ================================================================
# BUG-8: _match_initial が PROP_INI を使っているが
#         engineer_query→_match_initial でNOTION_DB全件スキャン
# ================================================================
# これはパフォーマンスの問題だが機能上は問題なし

# ================================================================
# BUG-9: engineer_query の Notion フィルタ PROP_RATE >= 75 が
#         案件単価75万未満の案件を全部弾いている
# ================================================================
# H.S単価70万 → 粗利5万以上 = 案件単価75万以上が必要 → フィルタは正しい
# しかし「岡本担当の案件は粗利3万OK」→ 案件単価73万でも提案できるが弾かれる
print("BUG-9候補: PROP_RATE>=75フィルタが岡本担当案件(粗利3万OK)で不当に弾く可能性")
print("  例: 案件単価73万、H.S単価70万 → 粗利3万 → 岡本案件なら提案できるのに弾かれる")

# ================================================================
# BUG-10: format_project_result で _text_prop(project, '案件名') をハードコード
# ================================================================
# フォーマット変更後の新コードで確認
if "_text_prop(project, '案件名')" in src:
    issues.append("BUG-10: format_project_result で '案件名' を直書き (PROP_PJNAMEを使うべき)")
if "_text_prop(project, '必要スキル')" in src or "_multi_select_prop(project, '必要スキル')" in src:
    issues.append("BUG-10b: format_project_result で '必要スキル' を直書き (PROP_REQSKを使うべき)")
if "_text_prop(project, '勤務地')" in src or "_text_prop(project, '勤務地')" in src:
    issues.append("BUG-10c: format_project_result で '勤務地' を直書き (PROP_LOCATIONを使うべき)")

# ================================================================
# BUG-11: project_query が全件スキャンしている (フィルタなし)
# ================================================================
idx_pq = src.find("def project_query")
idx_fetch = src.find("fetch_all_pages(PROJECT_DB_ID)", idx_pq)
idx_filter = src.find("filter_body", idx_pq)
if idx_fetch > 0 and (idx_filter < 0 or idx_filter > idx_fetch + 500):
    issues.append("BUG-11: project_query が filter_bodyなしで全件スキャン（遅い・1637件全部取る）")

# ================================================================
# BUG-12: format_engineer_result も日本語直書き多数
# ================================================================
for lit in ["'名前'", "'最寄り駅'", "'スキル'", "'稼働状況'", "'稼働可能日'", "'所属会社'", "'備考（LINEメモ）'"]:
    if (
        f"_text_prop(engineer, {lit})" in src
        or f"_multi_select_prop(engineer, {lit})" in src
        or f"_select_prop(engineer, {lit})" in src
        or f"_date_prop(engineer, {lit})" in src
    ):
        issues.append(f"BUG-12: format_engineer_result で {lit} を直書き（定数を使うべき）")

print()
print(f"発見した問題数: {len(issues)}件")
for i, issue in enumerate(issues, 1):
    print(f"  [{i}] {issue}")

print()
print("=" * 70)
print("優先度判定")
print("=" * 70)
print("【致命的・動作に影響】")
print("  BUG-9: 岡本案件が73-74万の場合にH.S(70万)がマッチしない")
print("  BUG-11: project_queryが全1637件スキャン(30秒以上かかる可能性)")
print()
print("【日本語直書き - Cloud Run環境で文字化けすると動作しない】")
print("  BUG-3/10/12: format_*関数の日本語プロパティ直書き")
print("  → Cloud Runのsrc/コンテナ内でUTF-8が保証されているなら問題なし")
print("  → ただし過去に文字化けバグがあったので確認が必要")
print()
print("【軽微】")
print("  BUG-1/2: format_project_result のイニシャル・最寄り駅取得")
