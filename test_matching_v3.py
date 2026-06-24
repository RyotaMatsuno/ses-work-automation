import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

# シンタックスチェック
r = subprocess.run(
    [sys.executable, "-m", "py_compile", "matching_v2/matching_v2.py"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
)
if r.returncode == 0:
    print("py_compile: OK")
else:
    print("py_compile ERROR:", r.stderr)

# get_min_grossテスト
r2 = subprocess.run(
    [
        sys.executable,
        "-c",
        'import sys; sys.path.insert(0,"matching_v2"); '
        "from matching_v2 import get_min_gross, is_within_business_days; "
        'assert get_min_gross("岡本","松野")==3, "岡本3万NG"; '
        'assert get_min_gross("松野","松野")==5, "松野5万NG"; '
        'assert get_min_gross("","") == 5, "不明5万NG"; '
        'assert is_within_business_days("2020-01-01T00:00:00.000Z", n=4) == False, "古い日付NG"; '
        'assert is_within_business_days("", n=4) == True, "空文字NG"; '
        'assert is_within_business_days("2020-01-01", n=4, interview_datetime="2026-06-01") == True, "面談済みNG"; '
        'print("全テストOK")',
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work",
)
print(r2.stdout.strip())
if r2.stderr:
    print("STDERR:", r2.stderr[:300])
