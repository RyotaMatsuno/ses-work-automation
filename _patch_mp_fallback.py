import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("mail_pipeline/mail_pipeline.py", encoding="utf-8") as f:
    content = f.read()

# classify_email関数を書き換える
# LLM失敗時にキーワードフォールバックを挟む

old_func = '''def classify_email(subject: str, body: str) -> dict:
    system = """あなたはSES業界の情報解析AIです。メールを解析してJSON形式のみで返答してください。

案件情報の場合:
{"type":"project","name":"案件名","required_skills":["Java"],"optional_skills":[],"price":0,"start_date":"","location":"","remote":"不明","period":"","interview_count":1,"foreign_ok":false,"note":"業務内容"}

人材情報の場合:
{"type":"engineer","name":"氏名","skills":["Java"],"price":0,"available_date":"","experience_years":0,"company":"","note":"備考"}

どちらでもない場合:
{"type":"other","note":"内容要約"}"""
    text = f"件名: {subject}\\n\\n{body[:2000]}"
    result = call_claude(system, text)
    try:
        clean = re.sub(r"```json|```", "", result).strip()
        parsed = json.loads(clean)
        return parsed if isinstance(parsed, dict) else {"type": "other", "note": "予期しない形式"}
    except:
        return {"type": "other", "note": "解析失敗"}'''

new_func = '''def _keyword_classify(subject: str, body: str) -> dict | None:
    """LLM失敗時のキーワードベース分類フォールバック。"""
    s = subject + " " + body[:500]
    s_lower = s.lower()

    # 案件キーワード
    project_kw = [
        "案件", "募集", "求人", "ポジション", "プロジェクト",
        "開発支援", "要員", "エンジニア募集", "即日", "7月",
        "稼働", "面談", "単価", "万円", "リモート", "常駐",
    ]
    # 人材キーワード
    engineer_kw = [
        "技術者", "人材", "スキルシート", "経歴書", "ご紹介",
        "ご提案", "弊社エンジニア", "候補者", "稼働可能",
        "弊社技術者", "human resource", "ご登録",
    ]
    # 除外（請求・挨拶等）
    other_kw = [
        "請求書", "見積", "挨拶", "お礼", "ありがとう",
        "休業", "営業時間", "ニュースレター", "メルマガ",
    ]

    for kw in other_kw:
        if kw in s:
            return None  # フォールバック不能

    eng_score = sum(1 for kw in engineer_kw if kw in s)
    prj_score = sum(1 for kw in project_kw if kw in s)

    if eng_score == 0 and prj_score == 0:
        return None

    # 単価を件名から抽出試み
    price = 0
    m = re.search(r'(\\d{2,3})万', subject)
    if m:
        price = int(m.group(1))

    if eng_score > prj_score:
        return {"type": "engineer", "name": "", "skills": [], "price": price,
                "available_date": "", "experience_years": 0, "company": "", "note": subject}
    else:
        return {"type": "project", "name": subject, "required_skills": [],
                "optional_skills": [], "price": price, "start_date": "",
                "location": "", "remote": "不明", "period": "",
                "interview_count": 1, "foreign_ok": False, "note": ""}


def classify_email(subject: str, body: str) -> dict:
    system = """あなたはSES業界の情報解析AIです。メールを解析してJSON形式のみで返答してください。

案件情報の場合:
{"type":"project","name":"案件名","required_skills":["Java"],"optional_skills":[],"price":0,"start_date":"","location":"","remote":"不明","period":"","interview_count":1,"foreign_ok":false,"note":"業務内容"}

人材情報の場合:
{"type":"engineer","name":"氏名","skills":["Java"],"price":0,"available_date":"","experience_years":0,"company":"","note":"備考"}

どちらでもない場合:
{"type":"other","note":"内容要約"}"""
    text = f"件名: {subject}\\n\\n{body[:2000]}"
    result = call_claude(system, text)
    try:
        clean = re.sub(r"```json|```", "", result).strip()
        parsed = json.loads(clean)
        if isinstance(parsed, dict) and parsed.get("type") in ("project", "engineer", "other"):
            return parsed
    except:
        pass

    # LLM失敗 → キーワードフォールバック
    fallback = _keyword_classify(subject, body)
    if fallback:
        log(f"  [keyword fallback] {fallback['type']}: {subject[:50]}")
        return fallback
    return {"type": "other", "note": "解析失敗"}'''

if old_func in content:
    new_content = content.replace(old_func, new_func)
    with open("mail_pipeline/mail_pipeline.py", "w", encoding="utf-8") as f:
        f.write(new_content)
    print("✅ キーワードフォールバック追加完了")
else:
    # 部分一致で探す
    print("完全一致せず。別アプローチで挿入します")
    idx = content.find("def classify_email")
    if idx != -1:
        print(f"classify_email found at {idx}")
        print(content[idx : idx + 200])
    else:
        print("classify_email not found")
