
path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\matching_v2.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

# ===== パッチ1: extract_engineer() に3フィールド追加 =====
OLD1 = '        "owner": get_select(props, "\u62c5\u5f53\u8005"),\n    }'
NEW1 = '        "owner": get_select(props, "\u62c5\u5f53\u8005"),\n        "raw_text": get_rich_text(props, "\u4eba\u54e1\u60c5\u5831\u539f\u6587"),\n        "file_path": get_rich_text(props, "\u6dfb\u4ed8\u30d5\u30a1\u30a4\u30eb\u30d1\u30b9"),\n        "drive_url": get_rich_text(props, "Drive\u30ea\u30f3\u30af"),\n    }'

if OLD1 in content:
    content = content.replace(OLD1, NEW1)
    print("PATCH1: OK")
else:
    print("PATCH1: NOT FOUND - checking raw bytes")
    # フォールバック: Shift-JIS混じりの可能性を考慮して行番号で直接置換
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'get_select' in line and i > 200 and i < 220:
            print(f"  Line {i+1}: {repr(line)}")
    print("PATCH1: SKIPPED")

# ===== パッチ2: build_skill_text_for_engineer 関数を judge_with_cache の直前に挿入 =====
BUILD_SKILL_FUNC = '''
def build_skill_text_for_engineer(engineer):
    """スキルシート原文 > Driveファイル > raw_text > multi_select の優先順位でスキルテキストを返す"""
    file_path = engineer.get("file_path", "")
    drive_url = engineer.get("drive_url", "")
    raw_text = engineer.get("raw_text", "")
    skills_list = engineer.get("skills", [])

    # ファイルパスがあれば読み込み（ローカルExcel/PDF）
    if file_path:
        try:
            import os
            if os.path.exists(file_path):
                ext = os.path.splitext(file_path)[1].lower()
                if ext in ('.txt', '.md'):
                    with open(file_path, encoding='utf-8', errors='ignore') as fp:
                        return fp.read()
        except Exception:
            pass

    # Drive URLがあればraw_textを優先（Driveダウンロードは非同期が必要なため今はスキップ）
    if raw_text:
        return raw_text

    # multi_selectにフォールバック
    return ", ".join(skills_list)

'''

INSERT_BEFORE = 'def judge_with_cache('
if INSERT_BEFORE in content and 'build_skill_text_for_engineer' not in content:
    content = content.replace(INSERT_BEFORE, BUILD_SKILL_FUNC + INSERT_BEFORE)
    print("PATCH2: OK")
elif 'build_skill_text_for_engineer' in content:
    print("PATCH2: ALREADY EXISTS")
else:
    print("PATCH2: INSERT POINT NOT FOUND")

# ===== パッチ3: judge_with_cache() 内の judge_skills_batch 呼び出しでスキルテキストを使う =====
OLD3 = '        [\n            {\n                "name": engineer["name"],\n                "skills": engineer.get("skills", []),\n            }\n            for engineer in engineers\n        ],'
NEW3 = '        [\n            {\n                "name": engineer["name"],\n                "skills": engineer.get("skills", []),\n                "skill_text": build_skill_text_for_engineer(engineer),\n            }\n            for engineer in engineers\n        ],'

if OLD3 in content:
    content = content.replace(OLD3, NEW3)
    print("PATCH3: OK")
else:
    print("PATCH3: NOT FOUND")

# ===== 書き込み =====
with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("WRITE: OK")

# ===== 構文チェック =====
import py_compile, sys
try:
    py_compile.compile(path, doraise=True)
    print("SYNTAX: OK")
except py_compile.PyCompileError as e:
    print(f"SYNTAX ERROR: {e}")
