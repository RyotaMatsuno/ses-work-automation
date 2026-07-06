import gspread, sys, io
from google.oauth2.service_account import Credentials

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

scopes = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file(
    r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\ses-work-automation-170e12155a49.json',
    scopes=scopes
)
gc = gspread.authorize(creds)
sh = gc.open_by_key('1ORBtxtGqLAwv3YU8CGeLX7gWFgvKOivMTCZZiWtYGfI')
terra = sh.worksheet('TERRA')

# Insert row at 35 (before 合計行)
terra.insert_row([
    'TERRA折半',      # 担当
    'BP',              # 区分
    '入場前',          # ステータス
    '佐藤礼奈',       # 氏名
    '2026/7',          # 参画時期
    '長期',            # 期間 (3ヵ月更新)
    'プロバイダ事務（平和島）',  # 案件/上位会社
    '380000',          # 単価(案件)
    '45',              # 支払サイト
    '',                # 勤怠表フロー
    '3ヵ月更新',       # 更新サイクル
    'プロバイダ事務',  # 業務内容
    '',                # 仕入先
    '330000',          # 仕入単価
    '50000',           # 粗利
    '25000',           # TERRA請求額
    '',                # 岡本払出
    '25000',           # 実入り
    'TERRA折半BP。粗利5万×50%=25,000請求。準委任。平和島。初回請求8月1日',  # 備考
    '',                # 7月稼働確定
    '準委任',          # 契約区分
], index=35)

print("[OK] 佐藤礼奈をTERRA Row35に追加")

# Verify
t_all = terra.get_all_values()
r35 = t_all[34]
print(f"Row35: [{r35[2]}] {r35[3]} | {r35[0]} | 単価={r35[7]} | 仕入={r35[13]} | 粗利={r35[14]} | TR請求={r35[15]} | 実入り={r35[17]}")
print(f"備考: {r35[18]}")
