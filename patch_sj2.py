
path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\skill_judge.py"
with open(path, encoding="utf-8") as f:
    lines = f.readlines()

# 278行目（client = Anthropic行）の後に挿入
# 279行目は空行、280行目がprompt = f"""
# 277行目と278行目の間に挿入（0-indexed: 277）
insert_at = 278  # 0-indexed、つまり279行目の前（client行の次の空行の後）

insert_code = [
    '\n',
    '    # skill_textがあればそれを優先してプロンプトに渡す\n',
    '    engineers_for_prompt = []\n',
    '    for eng in normalized_engineers:\n',
    '        skill_text = eng.get("skill_text", "")\n',
    '        if skill_text:\n',
    '            engineers_for_prompt.append({\n',
    '                "name": eng["name"],\n',
    '                "skill_description": skill_text,\n',
    '            })\n',
    '        else:\n',
    '            engineers_for_prompt.append({\n',
    '                "name": eng["name"],\n',
    '                "skills": eng["skills"],\n',
    '            })\n',
]

# engineers_for_promptが既にあるか確認
content = ''.join(lines)
if 'engineers_for_prompt = []' in content:
    print("ALREADY EXISTS - skipping insert")
else:
    new_lines = lines[:insert_at] + insert_code + lines[insert_at:]
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print("INSERT: OK")

import py_compile
try:
    py_compile.compile(path, doraise=True)
    print("SYNTAX: OK")
except py_compile.PyCompileError as e:
    print(f"SYNTAX ERROR: {e}")
