# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8")
import gspread
from google.oauth2.service_account import Credentials
from gspread.utils import a1_to_rowcol

KEY = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\google_credentials.json"
SS_ID = "1nSbYDRA9nzezksBDZacTpR4udEIhWOtixcwD7jTXLFk"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file(KEY, scopes=SCOPES)
gc = gspread.authorize(creds)
ws = gc.open_by_key(SS_ID).worksheet("経験者用")
vals = ws.get_all_values()


def g(a1):
    r, c = a1_to_rowcol(a1)
    try:
        return vals[r - 1][c - 1]
    except:
        return "∅"


print("=== スキルマトリクス最終状態 ===", flush=True)
print("[言語/年数]", flush=True)
for r in range(10, 18):
    a, e = g(f"A{r}"), g(f"E{r}")
    if a or e:
        print(f"  {a} : {e}", flush=True)
print("[OS/年数]", flush=True)
for r in [10, 11, 12, 13, 17, 18, 19]:
    p, s = g(f"P{r}"), g(f"S{r}")
    if p or s:
        print(f"  {p} : {s}", flush=True)
print("[ツール/年数]", flush=True)
for r in range(10, 18):
    x, ac = g(f"X{r}"), g(f"AC{r}")
    if x or ac:
        print(f"  {x} : {ac}", flush=True)
print("[工程/年数]", flush=True)
for r in range(10, 20):
    print(f"  {g(f'AH{r}')} : {g(f'AN{r}')}", flush=True)

print("\n=== 業務実績表 9枠 確認 ===", flush=True)
base = {1: 32, 2: 43, 3: 54, 4: 65, 5: 76, 6: 87, 7: 98, 8: 109, 9: 120}
for i, B in base.items():
    print(
        f"  枠{g(f'A{B}')}: {g(f'C{B + 3}')}〜{g(f'C{B + 5}')} ({g(f'C{B + 7}')}) / {g(f'X{B + 5}')} / {g(f'I{B}')[:24]}…",
        flush=True,
    )
print("\n[ALL DONE]", flush=True)
