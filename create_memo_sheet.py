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

# 備考・メモシートを新規作成
ws_memo = ss.add_worksheet(title="備考・メモ", rows=50, cols=5)

rows = [
    ["■ 契約マスター 運用ルール（2026-06-01確定）"],
    ["契約マスターはGoogleスプレッドシートのみで管理する。ローカルExcel（契約マスター_v6.xlsx）は使用しない。"],
    ["スプレッドシートURL: https://docs.google.com/spreadsheets/d/1ORBtxtGqLAwv3YU8CGeLX7gWFgvKOivMTCZZiWtYGfI/edit"],
    ["新規成約・退場・単価変更など全ての更新はスプレッドシートに直接行う。"],
    [""],
    ["■ 法人化タイミング（2026-06-01確定）"],
    ["推奨タイミング: 2027年上半期（1〜3月）"],
    ["今年中のアクション: 専従者給与届出のみ先行（年末年始前に提出）"],
    ["理由: 2026年内法人化との差額は約32〜47万円。FT直接契約移管（増収+47〜63万）と合わせて2027年1月設立が最適解"],
    [""],
    ["■ FP小坂さん 所属共有スキーム（2026-05確定）"],
    ["パターンA（小坂案件）: 松野岡本が所属と直接交渉→1社下抜き分×80%が松野岡本・20%が小坂（FP件数カウントなし）"],
    ["パターンB（松野岡本案件）: 小坂が所属情報提供→元々の利益そのまま+1社下抜き分×20%が小坂（FP件数カウントあり）"],
    [""],
    ["■ 直契約（鶴見有職研究所）（2026-06-01確定）"],
    ["月10万固定請求・翌月最終営業日払い・岡本払出5万/月・2026年6月〜"],
    ["請求先詳細は別途連携予定"],
    [""],
    ["■ 新営業報酬ルール（FT・2026-05確定）"],
    ["紹介のみ=請求額×20% / 自己完結=請求額×90%"],
    ["松野と成約=松野50%・岡本10%・新営業40% / 岡本と成約=岡本60%・新営業40%"],
    ["小坂代表と成約=粗利×50%請求→新営業に請求額×90%払出"],
]

ws_memo.update("A1", rows)
print("[OK] 備考・メモシート作成・内容入力完了", flush=True)
