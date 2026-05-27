
"""
matching_logic.py - SES マッチングロジック改善モジュール v1
webhook_server.py から import して使う
"""
import json
import re



import re as _re

def clean_note(note):
    if not note:
        return ''
    # 【案件要約】形式はそのまま
    if note.startswith('【案件要約】'):
        return note
    # 署名・挨拶を除去して案件情報部分のみ抽出
    skip_kw = ['TEL:', 'FAX:', '〒', 'https://', 'http://', '携帯:', 'mail :', 'HP：',
               '＝＝＝', '───', '___', '以上よろしく', 'メールアドレス', '@']
    # ■案件名 or 【案件名】 から始まる行を探す
    lines_all = note.splitlines()
    start_idx = None
    for i, line in enumerate(lines_all):
        if '■案件名' in line or '【案件名】' in line:
            start_idx = i
            break
    if start_idx is None:
        return note[:800]
    result_lines = []
    for line in lines_all[start_idx:]:
        # 署名ブロックの開始を検知
        if any(kw in line for kw in skip_kw):
            break
        # 区切り線（---、===、***）で終わり
        if _re.match(r'^[-=*_]{3,}$', line.strip()):
            break
        result_lines.append(line)
    return '\n'.join(result_lines).strip()

def deduplicate_projects(projects):
    """
    同一案件（スキル・場所・単価が近い）をグループ化し、単価最高のものだけ返す。
    残りも "duplicate_of" フラグを立てて保持（除外しない）。
    """
    if not projects:
        return projects

    used = [False] * len(projects)
    result = []

    for i, p in enumerate(projects):
        if used[i]:
            continue
        group = [p]
        used[i] = True
        pi_skills = set(p.get("required_skills", []) + p.get("optional_skills", []))
        pi_price = p.get("price", 0) or 0
        pi_loc = (p.get("location", "") or "").lower()

        for j in range(i + 1, len(projects)):
            if used[j]:
                continue
            q = projects[j]
            qj_skills = set(q.get("required_skills", []) + q.get("optional_skills", []))
            qj_price = q.get("price", 0) or 0
            qj_loc = (q.get("location", "") or "").lower()

            union = pi_skills | qj_skills
            overlap = len(pi_skills & qj_skills) / max(len(union), 1) if union else 0
            price_close = abs(pi_price - qj_price) <= 10
            loc_match = (pi_loc == qj_loc) or any(
                kw in pi_loc or kw in qj_loc
                for kw in ["remote", "リモート", "フルリモ"]
            )

            if overlap >= 0.7 and price_close and loc_match:
                group.append(q)
                used[j] = True

        # 単価最高のものを採用
        best = max(group, key=lambda x: x.get("price", 0) or 0)
        result.append(best)

    return result


def categorize_match(engineer_price, project_price, required_match, optional_match):
    """
    案件と人材の組み合わせをカテゴリ判定する。

    Returns:
        category: "ok" | "negotiation_needed" | "upfuri_candidate" | "ng"
        gross: 粗利（万円）
        adj_max, adj_mid, adj_min: 所属への調整依頼額
        upfuri_price: 上位への上振れ提案単価
    """
    ep = engineer_price or 0
    pp = project_price or 0
    gross = pp - ep if (pp > 0 and ep > 0) else None
    if ep > 0 and pp > 0 and (pp - ep) > 15:
        return {"category": "ng", "gross": gross, "reason": f"上振れ{pp-ep}万超（上限15万）"}

    req_all_ok = all(v for v in required_match.values()) if required_match else False
    opt_any_ok = any(v for v in optional_match.values()) if optional_match else False

    adj_max = adj_mid = adj_min = 0
    upfuri_price = 0
    category = "ng"

    if gross is None:
        # 単価情報なし → とりあえず表示する
        category = "unknown_price"
    elif gross >= 5:
        category = "ok"
    elif gross >= 0 or (gross < 0 and abs(gross) <= 5):
        # 粗利が0〜5未満、またはマイナス5以内 → 所属調整で救える可能性
        if req_all_ok or not required_match:
            category = "negotiation_needed"
            # 所属への調整依頼額: エンジニア単価を下げてもらう
            # 目標粗利5万を達成するために必要な値下げ幅
            shortfall = 5 - gross  # 例: 粗利2万なら不足3万
            adj_max = min(shortfall, 5)       # Max 5万
            adj_mid = min(shortfall, 3)       # 次点 3万
            adj_min = min(shortfall, 2)       # 最低 2万
        else:
            category = "ng"
    elif gross < -5:
        # 大幅マイナス → 上振れ候補チェック
        if req_all_ok and opt_any_ok:
            category = "upfuri_candidate"
            upfuri_price = ep + 7  # エンジニア単価 + 7万 = 上位への提案単価
        else:
            category = "ng"

    return {
        "category": category,
        "gross": gross,
        "adj_max": adj_max,
        "adj_mid": adj_mid,
        "adj_min": adj_min,
        "upfuri_price": upfuri_price,
        "req_all_ok": req_all_ok,
        "opt_any_ok": opt_any_ok,
    }


def build_affiliate_adjustment_text(project_name, engineer_name, adj_max, adj_mid, adj_min):
    """所属への単価調整依頼文を生成する"""
    lines = [
        f"{engineer_name}様について、{project_name}案件へのご提案を検討しております。",
        "つきましては、ご調整いただける範囲でご確認いただけますと幸いです。",
        "",
        f"  第1希望: {adj_max}万円のご調整",
        f"  第2希望: {adj_mid}万円のご調整",
        f"  第3希望: {adj_min}万円のご調整",
        "",
        "ご検討のほど何卒よろしくお願いいたします。",
    ]
    return "\n".join(lines)


def build_reverse_match_message_v2(eng_name, raw_matches, engineer_price):
    """
    改善版逆マッチングメッセージ。
    - OK / 調整必要 / 上振れ候補 / NG を区分け
    - 同一案件重複は deduplicate_projects で事前処理済み想定
    """
    if not raw_matches:
        return f"[registered] {eng_name}\n\nマッチする案件なし"

    ep = engineer_price or 0

    # カテゴリ付与
    categorized = []
    for m in raw_matches:
        pp = m.get("project_price", 0) or m.get("price", 0) or 0
        req_match = m.get("required_match", {})
        opt_match = m.get("optional_match", {})
        cat_info = categorize_match(ep, pp, req_match, opt_match)
        m["_cat"] = cat_info
        categorized.append(m)

    ok_list = [m for m in categorized if m["_cat"]["category"] == "ok"]
    nego_list = [m for m in categorized if m["_cat"]["category"] == "negotiation_needed"]
    upfuri_list = [m for m in categorized if m["_cat"]["category"] == "upfuri_candidate"]
    unknown_list = [m for m in categorized if m["_cat"]["category"] == "unknown_price"]
    ng_list = [m for m in categorized if m["_cat"]["category"] == "ng"]

    for lst in [ok_list, nego_list, upfuri_list, unknown_list]:
        lst.sort(key=lambda x: x.get("score", 0), reverse=True)

    lines = [f"[registered] {eng_name}"]
    total = len(ok_list) + len(nego_list) + len(upfuri_list) + len(unknown_list)
    lines.append(f"候補案件: {total}件\n")

    def skill_str(match_dict):
        if not match_dict:
            return ""
        return " ".join(f"{'O' if v else 'X'}{k}" for k, v in match_dict.items())

    # OK案件
    if ok_list:
        lines.append(f"[OK / 利益確保] {len(ok_list)}件")
        for i, m in enumerate(ok_list[:3], 1):
            pp = m.get("project_price", 0)
            gross = m["_cat"]["gross"]
            score = m.get("score", 0)
            lines.append(f"  {i}. {m.get('project_name', '不明')}")
            assignee = m.get("assignee", "")
            if assignee:
                lines.append(f"     会社: {assignee}")
            note = m.get("note", "")
            if note:
                lines.append(f"     内容: {clean_note(note)}")
            lines.append(f"     単価:{pp}万 粗利:{gross}万 スコア:{score}")
            rs = skill_str(m.get("required_match", {}))
            if rs:
                lines.append(f"     必須: {rs}")
            os_ = skill_str(m.get("optional_match", {}))
            if os_:
                lines.append(f"     尚可: {os_}")

    # 調整必要案件
    if nego_list:
        lines.append(f"\n[要調整 / 所属への単価交渉] {len(nego_list)}件")
        lines.append("  -> 所属にmax5万→3万→2万の順で調整依頼")
        for i, m in enumerate(nego_list[:3], 1):
            pp = m.get("project_price", 0)
            gross = m["_cat"]["gross"]
            cat = m["_cat"]
            lines.append(f"  {i}. {m.get('project_name', '不明')}")
            assignee = m.get("assignee", "")
            if assignee:
                lines.append(f"     会社: {assignee}")
            note = m.get("note", "")
            if note:
                lines.append(f"     内容: {clean_note(note)}")
            lines.append(f"     単価:{pp}万 現粗利:{gross}万")
            lines.append(f"     調整依頼額: max{cat['adj_max']}万 / {cat['adj_mid']}万 / {cat['adj_min']}万")

    # 上振れ候補案件
    if upfuri_list:
        lines.append(f"\n[上振れ候補 / 上位へ単価アップで提案] {len(upfuri_list)}件")
        lines.append("  -> 必須全○+尚可1つ以上○のため上振れ提案可")
        for i, m in enumerate(upfuri_list[:3], 1):
            pp = m.get("project_price", 0)
            up_price = m["_cat"]["upfuri_price"]
            lines.append(f"  {i}. {m.get('project_name', '不明')}")
            assignee = m.get("assignee", "")
            if assignee:
                lines.append(f"     会社: {assignee}")
            note = m.get("note", "")
            if note:
                lines.append(f"     内容: {clean_note(note)}")
            lines.append(f"     現単価:{pp}万 -> 上振れ提案:{up_price}万")

    # 単価不明
    if unknown_list:
        lines.append(f"\n[単価不明 / 要確認] {len(unknown_list)}件")
        for i, m in enumerate(unknown_list[:3], 1):
            lines.append(f"  {i}. {m.get('project_name', '不明')}")

    if not (ok_list or nego_list or upfuri_list or unknown_list):
        lines.append(f"[NG] {len(ng_list)}件 (スキル不足または単価差大きすぎ)")

    return "\n".join(lines)
