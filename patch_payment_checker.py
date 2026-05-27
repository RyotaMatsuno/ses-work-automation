import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

path = r'freee/payment_checker.py'
with open(path, 'r', encoding='utf-8') as f:
    src = f.read()

# 1. importブロックにjpholidayを追加
old_import = "from datetime import date, datetime"
new_import = "from datetime import date, datetime, timedelta"
src = src.replace(old_import, new_import, 1)

# 2. parse_date関数の直前に is_business_day / next_business_day を挿入
holiday_funcs = '''
import jpholiday as _jpholiday


def _is_business_day(d: date) -> bool:
    """土日・日本祝日でなければTrue"""
    return d.weekday() < 5 and not _jpholiday.is_holiday(d)


def _next_business_day(d: date) -> date:
    """d が休業日なら次の営業日を返す"""
    while not _is_business_day(d):
        d += timedelta(days=1)
    return d


def should_run_today() -> bool:
    """
    毎月15日・末日（28日タスク）に起動されるが、
    その日が土日祝の場合は翌営業日のみ実行する。
    実行日が「15日または月末の翌営業日」であればTrue。
    """
    today = date.today()
    year, month = today.year, today.month

    # 月末日を計算
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)

    target_days = [
        _next_business_day(date(year, month, 15)),  # 15日サイト
        _next_business_day(last_day),               # 月末サイト
    ]
    return today in target_days

'''

insert_before = "def parse_date"
src = src.replace(insert_before, holiday_funcs + insert_before, 1)

# 3. main()の先頭に「今日実行すべきか」チェックを追加
old_main = "def main() -> int:\n    args = parse_args()\n    return run(dry_run=args.dry_run)"
new_main = (
    "def main() -> int:\n"
    "    args = parse_args()\n"
    "    if not args.dry_run and not should_run_today():\n"
    "        logging.info(\"today is not a target business day; skipped\")\n"
    "        return 0\n"
    "    return run(dry_run=args.dry_run)"
)
src = src.replace(old_main, new_main, 1)

with open(path, 'w', encoding='utf-8') as f:
    f.write(src)
print("written")

# py_compile確認
import py_compile
try:
    py_compile.compile(path, doraise=True)
    print("py_compile: OK")
except py_compile.PyCompileError as e:
    print(f"py_compile: NG {e}")
