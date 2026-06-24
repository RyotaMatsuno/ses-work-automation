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

ws_ft = ss.worksheet("フラップテック")

# 15行目に追加（14行目=吉田祥平の次）
new_row = 15
ws_ft.insert_row(
    [
        "岡本折半",  # A: 担当
        "稼働中",  # B: ステータス
        "遠藤健太",  # C: 氏名
        "2026/7",  # D: 参画時期
        "長期",  # E: 期間
        "スウェル",  # F: 案件/上位
        600000,  # G: 案件単価
        550000,  # H: 仕入単価
        50000,  # I: 粗利
        34000,  # J: FT請求額（粗利5万×68%）
        17000,  # K: 岡本払出（FT請求÷2）
        17000,  # L: 実入り
        45,  # M: 支払サイト
        "上位からくる",  # N: 勤怠表フロー
        "",  # O: 送付先
        0,  # P: 木原さん分
        "単月更新",  # Q: 更新サイクル
        "岡本折半。粗利5万×68%=34,000÷2=17,000円。上位Rezon。赤坂見附リモート。精算140-200h上下割。7月入場→9月15日初回入金",  # R: 備考
    ],
    index=new_row,
)

print(f"[OK] 遠藤健太 行{new_row}に追加完了", flush=True)

# 確認
data = ws_ft.get_all_values()
print(f"追加後の行{new_row}: {data[new_row - 1][:8]}", flush=True)
