
path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\skill_judge.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

# normalized_engineers生成部分を修正
# skill_textがあればプロンプトに優先使用するよう変更

OLD = '''    normalized_engineers = [
        {
            "name": str(engineer.get("name", "")).strip(),
            "skills": _normalize_skill_list(engineer.get("skills", [])),
        }
        for engineer in engineers
        if str(engineer.get("name", "")).strip()
    ]'''

NEW = '''    normalized_engineers = [
        {
            "name": str(engineer.get("name", "")).strip(),
            "skills": _normalize_skill_list(engineer.get("skills", [])),
            "skill_text": str(engineer.get("skill_text", "")).strip(),
        }
        for engineer in engineers
        if str(engineer.get("name", "")).strip()
    ]'''

if OLD in content:
    content = content.replace(OLD, NEW)
    print("PATCH_NORMALIZED: OK")
else:
    print("PATCH_NORMALIZED: NOT FOUND")

# プロンプト部分でskill_textを優先使用するよう修正
OLD_PROMPT = '''    prompt = f"""
\u010d\u010d\u010d\u010d\u010d\u010d\u010d\u010d\u010d'''

# プロンプト生成の直前にskill_text優先のエンジニアリスト生成を追加
OLD2 = '    api_key = os.environ["ANTHROPIC_API_KEY"]\n    client = Anthropic(api_key=api_key)\n\n    prompt = f"""\n案件スキル:'
NEW2 = '''    api_key = os.environ["ANTHROPIC_API_KEY"]
    client = Anthropic(api_key=api_key)

    # skill_textがあればそれを優先してプロンプトに渡す
    engineers_for_prompt = []
    for eng in normalized_engineers:
        skill_text = eng.get("skill_text", "")
        if skill_text:
            engineers_for_prompt.append({
                "name": eng["name"],
                "skill_description": skill_text,
            })
        else:
            engineers_for_prompt.append({
                "name": eng["name"],
                "skills": eng["skills"],
            })

    prompt = f"""
案件スキル:'''

if OLD2 in content:
    content = content.replace(OLD2, NEW2)
    print("PATCH_PROMPT_PREFIX: OK")
else:
    print("PATCH_PROMPT_PREFIX: NOT FOUND - trying alternate")
    # cp932デコード文字が混じっている可能性があるため行番号で検索
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'api_key = os.environ' in line and i > 270:
            print(f"  Found at line {i+1}: {repr(line)}")

# エンジニアリストをプロンプトに渡す部分も変更
OLD3 = 'エンジニア一覧:\n{json.dumps(normalized_engineers, ensure_ascii=False)}'
NEW3 = 'エンジニア一覧:\n{json.dumps(engineers_for_prompt, ensure_ascii=False)}'

if OLD3 in content:
    content = content.replace(OLD3, NEW3)
    print("PATCH_PROMPT_ENGINEERS: OK")
else:
    print("PATCH_PROMPT_ENGINEERS: NOT FOUND")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("WRITE: OK")

import py_compile
try:
    py_compile.compile(path, doraise=True)
    print("SYNTAX: OK")
except py_compile.PyCompileError as e:
    print(f"SYNTAX ERROR: {e}")
