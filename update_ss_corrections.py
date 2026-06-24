# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8")
import gspread
from google.oauth2.service_account import Credentials

CREDS_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\google_credentials.json"
SS_ID = "1ORBtxtGqLAwv3YU8CGeLX7gWFgvKOivMTCZZiWtYGfI"
SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPES)
gc = gspread.authorize(creds)
ss = gc.open_by_key(SS_ID)

# ============================================================
# TERRAシート更新
# 列: A=1担当, B=2区分, C=3ステータス, D=4氏名, E=5参画, F=6期間
#     G=7案件, H=8単価, I=9サイト, J=10勤怠, K=11更新, L=12業務
#     M=13仕入先, N=14仕入単価, O=15粗利, P=16請求額, Q=17岡本払出
#     R=18実入り, S=19備考
# ============================================================
ws_t = ss.worksheet("TERRA")
data_t = ws_t.get_all_values()
name_row_t = {row[3]: i + 1 for i, row in enumerate(data_t) if len(row) > 3 and row[3]}

updates_t = []

# 1. 森 → 5月末終了
r = name_row_t.get("森")
if r:
    updates_t.append({"range": f"C{r}", "values": [["5月末終了"]]})
    updates_t.append({"range": f"F{r}", "values": [["5月末終了"]]})
    print(f"森 行{r}: ステータス・期間→5月末終了", flush=True)

# 2. 齋藤よしまさ → 岡本担当（A列）、区分P、備考追加
r = name_row_t.get("齋藤よしまさ")
if r:
    updates_t.append({"range": f"A{r}", "values": [["岡本"]]})
    updates_t.append({"range": f"H{r}", "values": [[430000]]})
    updates_t.append({"range": f"I{r}", "values": [[45]]})
    updates_t.append({"range": f"P{r}", "values": [[15000]]})
    updates_t.append({"range": f"Q{r}", "values": [[9000]]})
    updates_t.append(
        {
            "range": f"S{r}",
            "values": [
                [
                    "岡本担当。6割4割。初月5/15入場0.61人月→TERRA請求9,150円(7月入金)。6月〜フル15,000円。松野実入り5,988円/月・初月3,653円"
                ]
            ],
        }
    )
    print(f"齋藤 行{r}: 岡本担当・単価・請求・払出・備考入力", flush=True)

# 3. 佐々木 → 区分BPに変更（現在P）
r = name_row_t.get("佐々木")
if r:
    updates_t.append({"range": f"B{r}", "values": [["BP"]]})
    # 粗利・請求額・岡本払出も数値で入れる
    # 粗利=610000-560000=50000, 請求=50000*0.8=40000, 岡本払出=40000/2=20000, 松野実入り=20000
    updates_t.append({"range": f"O{r}", "values": [[50000]]})
    updates_t.append({"range": f"P{r}", "values": [[40000]]})
    updates_t.append({"range": f"Q{r}", "values": [[20000]]})
    updates_t.append({"range": f"R{r}", "values": [[20000]]})
    updates_t.append(
        {
            "range": f"S{r}",
            "values": [["岡本折半BP。粗利5万×80%=40,000請求。岡本50%払出=20,000。松野実入り20,000(税抜)"]],
        }
    )
    print(f"佐々木 行{r}: 区分BP・粗利・請求・払出・実入り入力", flush=True)

# 4. 吉田祥平TERRAは松野のみ → 担当列・備考のみ（FTは小坂折半）
r = name_row_t.get("吉田祥平")
if r:
    (updates_t.append({"range": f"A{r}", "values": [[""]]}),)  # 担当空欄（松野のみ）
    updates_t.append(
        {"range": f"S{r}", "values": [["TERRA側は松野のみ。TERRA粗利5万×80%=40,000請求。FTは小坂折半（FTシート参照）"]]}
    )
    print(f"吉田祥平 行{r}: TERRA担当空欄・備考更新", flush=True)

# バッチ更新実行
for upd in updates_t:
    ws_t.update(range_name=upd["range"], values=upd["values"])

print("\n[OK] TERRAシート更新完了", flush=True)

# ============================================================
# FTシート: 鶴川慶三の担当を「岡本新営業」→「岡本担当」に変更
# ============================================================
ws_ft = ss.worksheet("フラップテック")
data_ft = ws_ft.get_all_values()
name_row_ft = {row[2]: i + 1 for i, row in enumerate(data_ft) if len(row) > 2 and row[2]}

r = name_row_ft.get("鶴川慶三")
if r:
    # 担当列(A=col1)を「岡本担当」に変更
    ws_ft.update(range_name=f"A{r}", values=[["岡本担当"]])
    # 備考も更新（全額払出）
    ws_ft.update(
        range_name=f"R{r}",
        values=[["岡本担当（全額払出）。粗利7万×68%=47,600円を全額岡本へ払出。松野実入り0円。6月入場→8月15日初回入金"]],
    )
    print(f"FT鶴川慶三 行{r}: 岡本担当に変更・備考更新", flush=True)
else:
    print("FT鶴川慶三: NOT FOUND（スプレッドシートには未登録）", flush=True)
    # FTシートの最終行確認
    last_row = len(data_ft) + 1
    print(f"FT最終行: {last_row}", flush=True)

print("\n[DONE] 全更新完了", flush=True)
