# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WS = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py"
content = open(WS, encoding="utf-8").read()

# run_reverse_matching に #skill_skip 対応を追加
OLD = """def run_reverse_matching(engineer, projects):
    \"\"\"ルールベース逆マッチング（API不要）\"\"\"
    eng_skills = set(engineer.get("skills", []))
    eng_price = normalize_price(engineer.get("price", 0)) or 0
    matches = []
    for proj in projects:
        req_skills = set(proj.get("required_skills", []))
        opt_skills = set(proj.get("optional_skills", []))
        proj_price = normalize_price(proj.get("price", 0)) or 0
        gross = (proj_price - eng_price) if (proj_price > 0 and eng_price > 0) else 0
        if eng_price > 0 and proj_price > 0:
            if gross < 5: continue
            if gross > 15: continue
        req_match = {s: (s in eng_skills) for s in req_skills}
        opt_match = {s: (s in eng_skills) for s in opt_skills}
        if req_skills and not any(req_match.values()): continue"""

NEW = """def run_reverse_matching(engineer, projects):
    \"\"\"ルールベース逆マッチング（API不要）\"\"\"
    eng_skills = set(engineer.get("skills", []))
    eng_price = normalize_price(engineer.get("price", 0)) or 0
    # #skill_skip フラグ: 備考に記載がある場合はスキルフィルタを除外し単価のみでマッチ
    note = engineer.get("note", "") or ""
    skill_skip = "#skill_skip" in note
    matches = []
    for proj in projects:
        req_skills = set(proj.get("required_skills", []))
        opt_skills = set(proj.get("optional_skills", []))
        proj_price = normalize_price(proj.get("price", 0)) or 0
        gross = (proj_price - eng_price) if (proj_price > 0 and eng_price > 0) else 0
        if eng_price > 0 and proj_price > 0:
            if gross < 0: continue  # 粗利マイナスは除外
            if not skill_skip and gross > 15: continue  # 通常モードのみ上限チェック
        req_match = {s: (s in eng_skills) for s in req_skills}
        opt_match = {s: (s in eng_skills) for s in opt_skills}
        # スキルフィルタ（#skill_skipがある場合はスキップ）
        if not skill_skip:
            if req_skills and not any(req_match.values()): continue"""

if OLD in content:
    content = content.replace(OLD, NEW)
    print("run_reverse_matching #skill_skip対応 OK")
else:
    print("ERROR: 差し替え対象が見つかりません")

with open(WS, "w", encoding="utf-8") as f:
    f.write(content)
print("書き込み完了")
