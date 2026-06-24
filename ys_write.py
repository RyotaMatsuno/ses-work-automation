# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8")
import gspread
from google.oauth2.service_account import Credentials

KEY = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\google_credentials.json"
SS_ID = "1nSbYDRA9nzezksBDZacTpR4udEIhWOtixcwD7jTXLFk"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file(KEY, scopes=SCOPES)
gc = gspread.authorize(creds)
ws = gc.open_by_key(SS_ID).worksheet("経験者用")

PR = (
    "現在（2026年6月末まで）、某大手キャリアにてデータセンターのラック提供業務およびPOSサービスのテスト業務に従事しております。"
    "現場からの評価は非常に高く、本人の意向で開発系の案件を希望しております。\n"
    "テスト業務を中心に延べ約3年5ヶ月、スマホアプリ・POS・官公庁システムと多様な領域で品質担保に携わってきました。"
    "直近1年は教務システムの運用保守でPHP/Java/SQLも使用。SQL修正・不具合起票・テスト項目書作成〜エビデンス提出まで自走対応。\n"
    "IT業界以前には家電量販店・飲食店での接客・営業経験があり、コミュニケーション力とユーザー視点が強みです。\n"
    "取得資格：ITパスポート、情報セキュリティマネジメント(SG)、Rubyシルバー、Java2級、JavaSilver、JSTQB(Foundation)"
)


def C(rng, val):
    return {"range": rng, "values": [[val]]}


data = [
    # 言語 / 年数 (PHP・Java・SQL・Ruby、残り消去)
    C("A10", "PHP"),
    C("E10", "1年"),
    C("A11", "Java"),
    C("E11", "1年"),
    C("A12", "SQL"),
    C("E12", "1年2ヶ月"),
    C("A13", "Ruby"),
    C("E13", "資格のみ"),
    C("A14", ""),
    C("E14", ""),
    C("A15", ""),
    C("E15", ""),
    C("A16", ""),
    C("E16", ""),
    C("A17", ""),
    C("E17", ""),
    # ライブラリ/FW 消去（React/Spring/SpringBoot＝捏造Dev）
    C("I10", ""),
    C("L10", ""),
    C("I16", ""),
    C("L16", ""),
    C("I17", ""),
    C("L17", ""),
    # OS / 年数（Windows・Linux・Android・iOS、クラウド/AWS枠を転用）
    C("P10", "Windows"),
    C("S10", "3年5ヶ月"),
    C("P11", "Linux"),
    C("S11", "1年"),
    C("P12", "Android"),
    C("S12", "1年5ヶ月"),
    C("P13", "iOS"),
    C("S13", "1年"),
    # DB（Oracleのみ・短期、MySQL消去）
    C("P18", "Oracle"),
    C("S18", "短期"),
    C("P19", ""),
    C("S19", ""),
    # 開発環境/ツール（実ツールに置換、残り消去）
    C("X10", "Excel・Word・PowerPoint"),
    C("AC10", "3年5ヶ月"),
    C("X11", "Backlog"),
    C("AC11", "1年8ヶ月"),
    C("X12", "Teraterm"),
    C("AC12", "1年"),
    C("X13", "WinSCP・WinMerge"),
    C("AC13", "実務経験あり"),
    C("X14", ""),
    C("AC14", ""),
    C("X15", ""),
    C("AC15", ""),
    C("X16", ""),
    C("AC16", ""),
    C("X17", ""),
    C("AC17", ""),
    # 工程の年数（捏造8年系）を消去。ラベル(AH)は標準工程なので残す
    C("AN10", ""),
    C("AN11", ""),
    C("AN12", ""),
    C("AN13", ""),
    C("AN14", ""),
    C("AN15", ""),
    C("AN16", ""),
    C("AN17", ""),
    C("AN18", ""),
    C("AN19", ""),
    # 自己PR本文（A23＝A23:AR29結合・現状空）
    C("A23", PR),
]

ws.batch_update(data, value_input_option="RAW")
print(f"[WRITE OK] {len(data)} cells updated", flush=True)

# --- 検証: 主要セル読み直し ---
import time

time.sleep(1)
vals = ws.get_all_values()


def g(a1):
    from gspread.utils import a1_to_rowcol

    r, c = a1_to_rowcol(a1)
    try:
        return vals[r - 1][c - 1]
    except:
        return "(範囲外)"


print("\n=== 検証: 言語 ===", flush=True)
for r in range(10, 18):
    print(f"  A{r}={g(f'A{r}')!r} / E{r}={g(f'E{r}')!r}", flush=True)
print("=== 検証: OS/DB ===", flush=True)
for r in [10, 11, 12, 13, 17, 18, 19]:
    print(f"  P{r}={g(f'P{r}')!r} / S{r}={g(f'S{r}')!r}", flush=True)
print("=== 検証: ツール ===", flush=True)
for r in range(10, 18):
    print(f"  X{r}={g(f'X{r}')!r} / AC{r}={g(f'AC{r}')!r}", flush=True)
print("=== 検証: 工程 ラベル/年数 ===", flush=True)
for r in range(10, 20):
    print(f"  AH{r}={g(f'AH{r}')!r} / AN{r}={g(f'AN{r}')!r}", flush=True)
print("=== 検証: 自己PR(A23 冒頭60字) ===", flush=True)
print("  " + repr(g("A23")[:60]), flush=True)
print("\n[DONE]", flush=True)
