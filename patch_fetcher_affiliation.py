import sys

sys.stdout.reconfigure(encoding="utf-8")

# ① fetcher.py の normalize_engineer に affiliation フィールド追加
fetcher_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pipeline_v1\fetcher.py"
with open(fetcher_path, encoding="utf-8") as f:
    content = f.read()

old = '        "line_note": first_property_value(props, "備考(LINEメモ)", "備考（LINEメモ）") or "",'
new = (
    '        "line_note": first_property_value(props, "備考(LINEメモ)", "備考（LINEメモ）") or "",\n'
    '        "affiliation": property_value(props, "所属会社") or "",\n'
    '        "contact_name": property_value(props, "所属担当者名") or "",\n'
    '        "contact_email": property_value(props, "所属メール") or "",'
)

if old in content:
    content = content.replace(old, new)
    with open(fetcher_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("fetcher.py: affiliation追加OK")
else:
    print("fetcher.py: 対象行が見つからない")
    # 末尾確認
    idx = content.find("line_note")
    print(repr(content[idx : idx + 200]))
