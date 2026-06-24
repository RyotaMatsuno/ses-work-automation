# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LQ = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
content = open(LQ, encoding="utf-8").read()

# 1. 重複排除を先頭20文字→30文字に拡大（句読点違いを吸収）
OLD_DEDUP = """    # dedup: 先頭20文字で重複排除（同一案件の複数メール送信に対応）
    _seen: set[str] = set()
    _deduped: list[dict] = []
    for _p in projects:
        _k = _text_prop(_p, PROP_PJNAME)
        _k20 = _k[:20] if _k else ""
        if _k20 and _k20 not in _seen:
            _seen.add(_k20)
            _deduped.append(_p)
    projects = _deduped"""

NEW_DEDUP = r"""    # dedup: 句読点・記号を除去して先頭30文字で重複排除
    import re as _re_dedup
    _seen: set[str] = set()
    _deduped: list[dict] = []
    for _p in projects:
        _k = _text_prop(_p, PROP_PJNAME)
        # 句読点・全角記号を除去して正規化
        _k_norm = _re_dedup.sub(r'[、。・，．　\s【】（）()「」『』]', '', _k)[:30] if _k else ""
        if _k_norm and _k_norm not in _seen:
            _seen.add(_k_norm)
            _deduped.append(_p)
    projects = _deduped"""

if OLD_DEDUP in content:
    content = content.replace(OLD_DEDUP, NEW_DEDUP)
    print("重複排除ロジック修正 OK")
else:
    print("ERROR: 重複排除の対象箇所が見つかりません")

# 2. 4営業日フィルタを「情報取得日」基準に変更（created_timeではなく案件の鮮度で判断）
# 現状: created_time（Notion作成日）で4営業日チェック
# 修正: 情報取得日があればそちらを優先、なければcreated_timeを使う
OLD_AGE = """            if business_days_since(project.get("created_time")) > 4:
                continue"""

NEW_AGE = """            # 情報取得日があればそちらを優先（メールが溜まって翌日登録されるケースに対応）
            _info_date = _date_prop(project, bytes.fromhex("e68385e5a0b1e58f96e5be97e697a5").decode())  # 情報取得日
            _age_base = _info_date if _info_date else project.get("created_time", "")
            if business_days_since(_age_base) > 4:
                continue"""

if OLD_AGE in content:
    content = content.replace(OLD_AGE, NEW_AGE)
    print("4営業日フィルタ 情報取得日対応 OK")
else:
    print("ERROR: 4営業日フィルタの対象箇所が見つかりません")

with open(LQ, "w", encoding="utf-8") as f:
    f.write(content)
print("line_query.py 書き込み完了")
