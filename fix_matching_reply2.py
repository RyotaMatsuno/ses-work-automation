path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

# build_matching_result_reply関数全体を差し替え
old_func = """def build_matching_result_reply():

    result_path = os.path.join(os.path.dirname(__file__), '..', 'matching_v2', 'result.json')

    if not os.path.exists(result_path):

        return "【マッチング結果】\\n結果なし"

    try:

        with open(result_path, 'r', encoding='utf-8') as f:

            data = json.load(f)

    except Exception as e:

        print(f"[matching_reply] result.json read error: {e}")

        return "【マッチング結果】\\n結果なし"

    items = data if isinstance(data, list) else data.get("projects", [])

    if not isinstance(items, list):

        return "【マッチング結果】\\n結果なし"

    lines = [f"【マッチング結果】{datetime.now().strftime('%Y-%m-%d %H:%M')}"]

    project_count = 0

    number_labels = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨", "⑩"]

    for item in items:

        if not isinstance(item, dict):

            continue

        candidates = item.get("candidates") or []

        if not candidates:

            continue

        project = item.get("project") or {}

        project_name = project.get("name") or item.get("project_name") or "（案件名なし）"

        project_url = project.get("url") or item.get("project_url") or ""

        lines.append("")

        lines.append(f"■ {project_name}（{len(candidates)}名マッチ）")

        if project_url:

            lines.append(str(project_url))

        for index, candidate in enumerate(candidates[:2]):

            if not isinstance(candidate, dict):

                continue

            engineer = candidate.get("engineer") or {}

            name = engineer.get("name") or candidate.get("engineer_name") or candidate.get("name") or "（名前なし）"

            if candidate.get("needs_check"):

                name += " [要確認]"

            price = engineer.get("price") if engineer.get("price") is not None else candidate.get("price")

            price_text = f"{price}万" if price not in (None, "") else "未設定"

            lines.append(f"  {number_labels[index]} {name} /{price_text}")

        if len(candidates) > 2:

            lines.append(f"  他{len(candidates) - 2}名")

        project_count += 1

    if project_count == 0:

        return "【マッチング結果】\\n結果なし"

    return "\\n".join(lines)"""

new_func = '''def build_matching_result_reply():
    """Notion DBからリアルタイムでマッチング結果を取得してフォーマット"""
    try:
        # アクティブな案件を取得
        project_pages = notion_query(NOTION_PROJECT_DB_ID, {
            "or": [
                {"property": "ステータス", "select": {"equals": "募集中"}},
                {"property": "ステータス", "select": {"equals": "稼働中"}},
            ]
        })
        # 稼働可能なエンジニアを取得
        engineer_pages = notion_query(NOTION_ENGINEER_DB_ID, {
            "property": "稼働状況", "select": {"equals": "稼働可能"}
        })
    except Exception as e:
        print(f"[matching_reply] notion error: {e}")
        return "【マッチング結果】\\nデータ取得失敗"

    if not project_pages or not engineer_pages:
        return f"【マッチング結果】{datetime.now().strftime('%Y-%m-%d %H:%M')}\\n\\n案件または人材データなし（案件:{len(project_pages)}件 人材:{len(engineer_pages)}名）"

    number_labels = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨", "⑩"]
    lines = [f"【マッチング結果】{datetime.now().strftime('%Y-%m-%d %H:%M')}"]
    match_count = 0

    for pp in project_pages:
        props = pp.get("properties", {})
        # 案件名
        name_items = props.get("案件名", {}).get("title", [])
        proj_name = name_items[0].get("plain_text", "名称未設定") if name_items else "名称未設定"
        # 必須スキル
        req_skills = [o["name"] for o in props.get("必要スキル", {}).get("multi_select", [])]
        proj_price = props.get("単価（万円）", {}).get("number") or 0
        notion_url = f"https://www.notion.so/{pp['id'].replace('-', '')}"

        if not req_skills:
            continue  # スキル指定なし案件はスキップ

        # エンジニアとのスキルマッチング
        matched = []
        for ep in engineer_pages:
            eprops = ep.get("properties", {})
            ename_items = eprops.get("名前", {}).get("title", [])
            ename = ename_items[0].get("plain_text", "不明") if ename_items else "不明"
            eskills = [o["name"] for o in eprops.get("スキル", {}).get("multi_select", [])]
            eprice = eprops.get("単価（万円）", {}).get("number") or 0

            # 必須スキルが1つ以上一致すればマッチとする
            hit = [s for s in req_skills if s in eskills]
            if not hit:
                continue
            # 粗利チェック（5万以上）
            if eprice > 0 and proj_price > 0 and (proj_price - eprice) < 5:
                continue
            matched.append({"name": ename, "price": eprice, "hit": hit})

        if not matched:
            continue

        lines.append("")
        lines.append(f"■ {proj_name}（{len(matched)}名マッチ）")
        lines.append(notion_url)
        for idx, m in enumerate(matched[:2]):
            price_str = f"{m['price']}万" if m['price'] else "未設定"
            lines.append(f"  {number_labels[idx]} {m['name']} /{price_str}")
        if len(matched) > 2:
            lines.append(f"  他{len(matched)-2}名")
        match_count += 1

    if match_count == 0:
        return f"【マッチング結果】{datetime.now().strftime('%Y-%m-%d %H:%M')}\\n\\n現在マッチング候補なし\\n（案件:{len(project_pages)}件 人材:{len(engineer_pages)}名で検索済み）"

    return "\\n".join(lines)'''

if old_func in content:
    content = content.replace(old_func, new_func)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("差し替え完了")
else:
    # 関数の先頭だけでマッチング試みる
    print("完全一致せず。関数の先頭を探します...")
    idx = content.find("def build_matching_result_reply():")
    print(f"関数位置: {idx}")
