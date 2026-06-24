import sys

sys.stdout.reconfigure(encoding="utf-8")

with open("matching_v2/matching_v2.py", encoding="utf-8") as f:
    content = f.read()

# バックアップ
with open("matching_v2/matching_v2.py.bak_0526_v3", "w", encoding="utf-8") as f:
    f.write(content)
print("backup: OK")

# 1) importブロックにjpholidayとdatetime追加
# 既存のimport requests の後に追加
old_import = "import requests\n"
new_import = (
    "import requests\n"
    "from datetime import datetime, timedelta\n"
    "try:\n"
    "    import jpholiday\n"
    "    _JPHOLIDAY_AVAILABLE = True\n"
    "except ImportError:\n"
    "    _JPHOLIDAY_AVAILABLE = False\n"
)

if "jpholiday" not in content:
    if "from datetime import datetime" in content:
        # datetimeは既にある場合はjpholidayだけ追加
        new_import = (
            "import requests\n"
            "try:\n"
            "    import jpholiday\n"
            "    _JPHOLIDAY_AVAILABLE = True\n"
            "except ImportError:\n"
            "    _JPHOLIDAY_AVAILABLE = False\n"
        )
    content = content.replace(old_import, new_import, 1)
    print("import追加: OK")
else:
    print("import: 既に存在")

# 2) is_within_business_days()をget_min_gross()の直後に追加
func = '''

def is_within_business_days(created_at_str: str, n: int = 4, interview_datetime: str = None) -> bool:
    """
    受信日からn営業日以内（土日祝除く）かどうかを返す。
    interview_datetimeが指定されている場合は常にTrueを返す（面談設定済み案件）。
    """
    # 面談設定済み案件は有効期限チェックをスキップ
    if interview_datetime:
        return True
    if not created_at_str:
        return True  # 日付不明は通す
    try:
        # ISO 8601 → date
        created_date = datetime.fromisoformat(
            created_at_str.replace('Z', '+00:00')
        ).date()
    except Exception:
        return True  # パース失敗は通す

    today = datetime.now().date()
    if today <= created_date:
        return True  # 当日受信は必ず有効

    count = 0
    d = created_date
    while d < today:
        d += timedelta(days=1)
        if d.weekday() >= 5:
            continue  # 土日除外
        if _JPHOLIDAY_AVAILABLE and jpholiday.is_holiday(d):
            continue  # 祝日除外
        count += 1

    return count <= n

'''

target = "\ndef build_skill_text_for_engineer"
if "is_within_business_days" not in content:
    content = content.replace(target, func + "\ndef build_skill_text_for_engineer", 1)
    print("is_within_business_days追加: OK")
else:
    print("is_within_business_days: 既に存在")

# 3) main()のprojects取得後にフィルタ追加
old_print = '    print(f"募集中案件: {len(projects)}件 / 稼働可能エンジニア: {len(engineers)}名")'
new_print = """    # 案件有効期限フィルタ（受信から4営業日、土日祝除く）
    before_count = len(projects)
    projects = [
        p for p in projects
        if is_within_business_days(
            p.get("created_time", ""),
            n=4,
            interview_datetime=p.get("interview_datetime")
        )
    ]
    print(f"有効期限フィルタ: {before_count}件 -> {len(projects)}件（{before_count - len(projects)}件除外）")

    print(f"募集中案件: {len(projects)}件 / 稼働可能エンジニア: {len(engineers)}名")"""

if "有効期限フィルタ" not in content:
    content = content.replace(old_print, new_print, 1)
    print("有効期限フィルタ追加: OK")
else:
    print("有効期限フィルタ: 既に存在")

# 4) extract_project()でcreated_timeを取得
old_extract_return = """        "raw_body": raw_body,
    }"""
new_extract_return = """        "raw_body": raw_body,
        "created_time": page.get("created_time", ""),
        "interview_datetime": get_date(props, "面談日時"),
    }"""

if '"created_time": page.get' not in content:
    # extract_projectの返値のみ差し替え（extract_engineerと区別するため案件名を使う）
    # 最初のraw_body": raw_body,\n    }がextract_project
    content = content.replace(old_extract_return, new_extract_return, 1)
    print("extract_project created_time追加: OK")
else:
    print("created_time: 既に存在")

# 書き込み
with open("matching_v2/matching_v2.py", "w", encoding="utf-8") as f:
    f.write(content)
print("ファイル書き込み: OK")
