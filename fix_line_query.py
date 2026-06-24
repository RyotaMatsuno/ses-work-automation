# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LQ = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
content = open(LQ, encoding="utf-8").read()

# engineer_query内のマッチングロジックを修正
OLD = """        matched: list[dict] = []
        for project in projects:
            if _select_prop(project, PROP_STATUS) not in (VAL_RECRUITING, VAL_ADJUSTING):
                continue
            if business_days_since(project.get("created_time")) > 4:
                continue
            required = _multi_select_prop(project, PROP_REQSK)
            if not required:
                continue  # スキル未設定案件はマッチング対象外
            if not skill_match(required, eng_skills):
                continue
            budget = _number_prop(project, PROP_RATE)
            if budget > 150:
                continue  # 異常単価除外
            _th = _gross_threshold(_select_prop(project, PROP_ASSIGNEE))
            gross  = calc_gross_profit(budget, eng_rate)
            if gross > 15:
                continue  # 粗利上限15万超は単価乖離大きすぎ・スキルミスマッチリスク
            if gross < 0:
                continue  # 粗利マイナス=交渉しても利益見込めない
            if gross < _th:
                continue
            matched.append({"page": project, "gross_profit": gross})"""

NEW = """        # #skill_skip フラグ確認（備考に記載がある場合はスキルフィルタ除外・単価のみでマッチ）
        memo = _text_prop(engineer, PROP_MEMO)
        skill_skip = "#skill_skip" in memo

        matched: list[dict] = []
        for project in projects:
            if _select_prop(project, PROP_STATUS) not in (VAL_RECRUITING, VAL_ADJUSTING):
                continue
            if business_days_since(project.get("created_time")) > 4:
                continue
            required = _multi_select_prop(project, PROP_REQSK)
            budget = _number_prop(project, PROP_RATE)
            if budget > 150:
                continue  # 異常単価除外
            _th = _gross_threshold(_select_prop(project, PROP_ASSIGNEE))
            gross  = calc_gross_profit(budget, eng_rate)
            if skill_skip:
                # #skill_skip: 単価のみでマッチ（スキルフィルタ除外・粗利上限なし）
                if gross < 0:
                    continue
                if gross < _th:
                    continue
            else:
                # 通常モード: スキルフィルタ + 粗利上限15万
                if not required:
                    continue  # スキル未設定案件はマッチング対象外
                if not skill_match(required, eng_skills):
                    continue
                if gross > 15:
                    continue  # 粗利上限15万超は単価乖離大きすぎ
                if gross < 0:
                    continue
                if gross < _th:
                    continue
            matched.append({"page": project, "gross_profit": gross})"""

if OLD in content:
    content = content.replace(OLD, NEW)
    print("line_query.py engineer_query #skill_skip対応 OK")
else:
    print("ERROR: 差し替え対象が見つかりません")

with open(LQ, "w", encoding="utf-8") as f:
    f.write(content)
print("書き込み完了")
