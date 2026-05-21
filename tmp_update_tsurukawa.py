
import gspread, json
from google.oauth2.service_account import Credentials

CREDS_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\google_credentials.json"
SS_ID = "1ORBtxtGqLAwv3YU8CGeLX7gWFgvKOivMTCZZiWtYGfI"
SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

creds = Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPES)
gc = gspread.authorize(creds)
ss = gc.open_by_key(SS_ID)
ws = ss.worksheet("フラップテック")

# FTシートのヘッダー（行3）:
# A担当, B-ステータス, C-氏名, D-参画時期, E-期間, F-案件/上位,
# G-案件単価, H-仕入単価, I-粗利, J-FT請求額, K-岡本払出, L-実入り,
# M-支払サイト, N-勤怠表フロー, O-送付先, P-木原さん分, Q-更新サイクル, R-備考

# 粗利・請求額計算
tanka  = 720000
shiire = 650000
profit = tanka - shiire          # 70,000
ft_req = int(profit * 0.68)      # 47,600
okamoto_pay = int(ft_req * 0.20) # 9,520（新営業マージン20%）
jissiri = ft_req - okamoto_pay   # 38,080

# 行14の鶴川を全列更新
row_data = [
    "岡本新営業",       # A: 担当
    "稼働中",           # B: ステータス
    "鶴川慶三",         # C: 氏名
    "2026/5",           # D: 参画時期
    "長期",             # E: 期間
    "アバンテック",     # F: 案件/上位
    tanka,              # G: 案件単価
    shiire,             # H: 仕入単価
    profit,             # I: 粗利
    ft_req,             # J: FT請求額
    okamoto_pay,        # K: 岡本払出
    jissiri,            # L: 実入り
    45,                 # M: 支払サイト
    "LINE",             # N: 勤怠表フロー
    "",                 # O: 送付先
    0,                  # P: 木原さん分
    "単月更新",         # Q: 更新サイクル
    "小売・メーカー・卸向け基幹システム開発 / 精算140-200(中間割170) / 超過4,230円 仕入3,820円 / 岡本新営業マージン粗利×68%×20%=9,520円/月",  # R: 備考
]

ws.update(f"A14:R14", [row_data])
print(f"FT 行14 鶴川慶三 更新完了")
print(f"  案件単価: {tanka:,}  仕入: {shiire:,}  粗利: {profit:,}")
print(f"  FT請求: {ft_req:,}  岡本払出: {okamoto_pay:,}  実入り: {jissiri:,}")
