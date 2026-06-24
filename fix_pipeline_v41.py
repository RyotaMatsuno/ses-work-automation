"""
mail_pipeline.py バグ修正 v4.1
修正1: 日付バリデーション - ISO 8601でない文字列はNoneに変換してNotionに渡さない
修正2: classify_email の返り値がlistの場合のガード追加
"""

from pathlib import Path

fpath = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\mail_pipeline.py")
content = fpath.read_text(encoding="utf-8")
original = content

# ===== 修正1: 日付バリデーション関数を追加 =====
# register_project と register_engineer の start_date / available_date 処理前にバリデーションを挟む
# ISO 8601 = YYYY-MM-DD 形式のみ通す

date_validator = '''
def is_valid_iso_date(s) -> bool:
    """ISO 8601 (YYYY-MM-DD) 形式かどうか確認"""
    if not s or not isinstance(s, str):
        return False
    import re
    return bool(re.match(r'^\\d{4}-\\d{2}-\\d{2}$', s.strip()))

'''

# log関数の直後に挿入
content = content.replace("# ===== 処理済みID管理 =====", date_validator + "# ===== 処理済みID管理 =====")

# register_project の start_date 処理を修正
old_proj_date = (
    '    if info.get("start_date"):\n        properties["開始日"] = {"date": {"start": info["start_date"]}}\n'
)
new_proj_date = (
    '    if is_valid_iso_date(info.get("start_date")):\n'
    '        properties["開始日"] = {"date": {"start": info["start_date"].strip()}}\n'
)
content = content.replace(old_proj_date, new_proj_date)

# register_engineer の available_date 処理を修正
old_eng_date = (
    '    if info.get("available_date"):\n'
    '        properties["稼働可能日"] = {"date": {"start": info["available_date"]}}\n'
)
new_eng_date = (
    '    if is_valid_iso_date(info.get("available_date")):\n'
    '        properties["稼働可能日"] = {"date": {"start": info["available_date"].strip()}}\n'
)
content = content.replace(old_eng_date, new_eng_date)

# ===== 修正2: classify_email の返り値ガード =====
old_classify = (
    "    try:\n"
    '        clean = re.sub(r"```json|```", "", result).strip()\n'
    "        return json.loads(clean)\n"
    "    except:\n"
    '        return {"type": "other", "note": "解析失敗"}'
)
new_classify = (
    "    try:\n"
    '        clean = re.sub(r"```json|```", "", result).strip()\n'
    "        parsed = json.loads(clean)\n"
    "        if isinstance(parsed, dict):\n"
    "            return parsed\n"
    "        # listが返ってきた場合は先頭要素を使う\n"
    "        if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):\n"
    "            return parsed[0]\n"
    '        return {"type": "other", "note": "予期しない形式"}\n'
    "    except:\n"
    '        return {"type": "other", "note": "解析失敗"}'
)
content = content.replace(old_classify, new_classify)

if content == original:
    print("WARNING: 変更なし - 対象文字列が見つからなかった")
else:
    fpath.write_text(content, encoding="utf-8")
    print("修正完了 (v4.1)")

# 確認
checks = [
    ("is_valid_iso_date" in content, "is_valid_iso_date 関数追加"),
    ('is_valid_iso_date(info.get("start_date"))' in content, "案件日付バリデーション"),
    ('is_valid_iso_date(info.get("available_date"))' in content, "人材日付バリデーション"),
    ("isinstance(parsed, list)" in content, "list返り値ガード"),
]
for ok, label in checks:
    print(f"  {'OK' if ok else 'NG'} {label}")
