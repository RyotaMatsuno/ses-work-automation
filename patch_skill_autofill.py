path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pipeline_v1\skill_autofill.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# parse_skill_json を修正（空文字・JSONDecodeError対応）
old = """def parse_skill_json(text: str) -> dict[str, list[str]]:
    data = json.loads(text.strip())
    if not isinstance(data, dict):
        return {"required_skills": [], "optional_skills": []}"""

new = """def parse_skill_json(text: str) -> dict[str, list[str]]:
    text = text.strip().replace("```json", "").replace("```", "").strip()
    if not text:
        return {"required_skills": [], "optional_skills": []}
    try:
        data = json.loads(text)
    except Exception:
        return {"required_skills": [], "optional_skills": []}
    if not isinstance(data, dict):
        return {"required_skills": [], "optional_skills": []}"""

# extract_skills のreturn部分も修正（例外catch追加）
old2 = """    return parse_skill_json("".join(text_parts))"""
new2 = """    try:
        return parse_skill_json("".join(text_parts))
    except Exception as e:
        print(f"[skill_autofill] parse error: {e}")
        return {"required_skills": [], "optional_skills": []}"""

content = content.replace(old, new).replace(old2, new2)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("patched OK")
