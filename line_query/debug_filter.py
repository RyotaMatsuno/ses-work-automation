import sys

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query")
if "line_query" in sys.modules:
    del sys.modules["line_query"]
import line_query as lq

pages = lq.fetch_all_pages(lq.ENGINEER_DB_ID)

# H.Sを特定
hs_engineer = None
for p in pages:
    if lq._match_initial(p, "HS"):
        hs_engineer = p
        break

if not hs_engineer:
    print("H.S not found")
else:
    name = lq._text_prop(hs_engineer, "名前")
    skills = lq._multi_select_prop(hs_engineer, "スキル")
    rate = lq._number_prop(hs_engineer, "単価（万円）")
    print(f"Engineer: {name}, skills={skills}, rate={rate}")

    # 案件DB全件取得してフィルタ過程を追跡
    projects = lq.fetch_all_pages(lq.PROJECT_DB_ID)
    print(f"Total projects: {len(projects)}")

    skip_status = skip_fresh = skip_skill = skip_profit = pass_count = 0
    for proj in projects:
        status = lq._select_prop(proj, "ステータス")
        if status != "募集中":
            skip_status += 1
            continue
        days = lq.business_days_since(proj.get("last_edited_time"))
        if days > 4:
            skip_fresh += 1
            continue
        required = lq._multi_select_prop(proj, "必要スキル")
        if not lq.skill_match(required, skills):
            skip_skill += 1
            continue
        budget = lq._number_prop(proj, "単価（万円）")
        gross = lq.calc_gross_profit(budget, rate)
        threshold = lq._gross_threshold(lq._select_prop(proj, "担当者"))
        if gross < threshold:
            skip_profit += 1
            continue
        pass_count += 1
        pname = lq._text_prop(proj, "案件名")
        print(f"  MATCH: {pname} budget={budget} gross={gross}")

    with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\filter_debug.txt", "w", encoding="utf-8") as f:
        f.write(f"Engineer: {name}, skills={skills}, rate={rate}\n")
        f.write(
            f"Total: {len(projects)}, status_skip={skip_status}, fresh_skip={skip_fresh}, skill_skip={skip_skill}, profit_skip={skip_profit}, pass={pass_count}\n"
        )

    print(
        f"\nTotal={len(projects)} status_skip={skip_status} fresh_skip={skip_fresh} skill_skip={skip_skill} profit_skip={skip_profit} pass={pass_count}"
    )
