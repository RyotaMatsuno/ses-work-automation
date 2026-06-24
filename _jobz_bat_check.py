import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES = os.getcwd()

# ── bat ファイル内容確認 ──────────────────────────────
print("■ wd_matching_v3.bat 内容")
bat = os.path.join(SES, "wd_matching_v3.bat")
if os.path.exists(bat):
    with open(bat, encoding="cp932", errors="replace") as f:
        print(f.read())
else:
    print("  未存在 → matching_v3.bat を探す")
    for fn in os.listdir(SES):
        if "match" in fn.lower() and fn.endswith(".bat"):
            print(f"  発見: {fn}")
            with open(os.path.join(SES, fn), encoding="cp932", errors="replace") as f:
                print(f.read())

print("\n■ wd_mail_pipeline.bat 内容")
bat2 = os.path.join(SES, "wd_mail_pipeline.bat")
if os.path.exists(bat2):
    with open(bat2, encoding="cp932", errors="replace") as f:
        print(f.read())
else:
    print("  未存在")

# ── 直接 bat を実行して結果確認（matching） ───────────
print("\n■ wd_matching_v3.bat 直接実行テスト（5秒タイムアウト）")
if os.path.exists(bat):
    r = subprocess.run(
        bat, capture_output=True, text=True, encoding="cp932", errors="replace", cwd=SES, timeout=15, shell=True
    )
    print(f"  returncode: {r.returncode}")
    print(f"  stdout: {r.stdout[:1000]}")
    print(f"  stderr: {r.stderr[:1000]}")
else:
    print("  bat未存在のためスキップ")

# ── matching_v3 ディレクトリ直下のPythonファイル確認 ──
print("\n■ matching_v3/ 直下ファイル一覧")
mv3 = os.path.join(SES, "matching_v3")
for fn in sorted(os.listdir(mv3)):
    fp = os.path.join(mv3, fn)
    if os.path.isfile(fp):
        sz = os.path.getsize(fp)
        print(f"  {fn} ({sz}b)")
    else:
        print(f"  {fn}/")

# ── SES_MatchingV3 のイベントログ確認 ─────────────────
print("\n■ Windows イベントログ（SES_MatchingV3 直近3件）")
r = subprocess.run(
    [
        "powershell",
        "-Command",
        "Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-TaskScheduler/Operational'; Id=201,203} -MaxEvents 10 | "
        "Where-Object {$_.Message -like '*MatchingV3*' -or $_.Message -like '*matching*'} | "
        "Select-Object TimeCreated, Id, Message | Format-List",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    timeout=15,
)
print(r.stdout[:2000] if r.stdout else "  イベントログ取得失敗")
if r.stderr:
    print(f"  stderr: {r.stderr[:200]}")
