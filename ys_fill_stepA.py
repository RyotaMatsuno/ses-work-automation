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


def C(rng, val):
    return {"range": rng, "values": [[val]]}


data = []

# --- スキルDB修正（本物=MySQL/db2 知識、Oracleは実務無しなので置換）---
data += [C("P18", "MySQL"), C("S18", "知識"), C("P19", "IBM db2"), C("S19", "知識")]

# --- 工程の年数（要件定義〜製造=空欄／テスト系配分／運用保守1年）---
data += [
    C("AN10", ""),
    C("AN11", ""),
    C("AN12", ""),
    C("AN13", ""),
    C("AN14", "1年"),  # 単体テスト
    C("AN15", "1年"),  # 結合テスト
    C("AN16", "1年6ヶ月"),  # 総合テスト
    C("AN17", "1年"),  # 運用・保守
    C("AN18", "1年6ヶ月"),  # テスト設計作成
    C("AN19", "1年6ヶ月"),
]  # テスト仕様書作成

# --- 自己PR（詳しい版・現状を教務運用保守に更新）---
PR = (
    "取得資格：情報セキュリティマネジメント(SG)、Ruby技術者認定試験(Silver)、Oracle認定Javaプログラマ(Silver)、Javaプログラミング能力認定試験(2級)、JSTQB(Foundation)\n\n"
    "現在（2026年6月末まで）、教務システムの運用保守に従事しております。ヘルプデスクからのエスカレーション対応、仕様と不具合の切り分け、SQLによるデータ補正、不具合チケットの起票、テスト（テスト項目書の作成・テスト実施・エビデンス作成）まで自走して対応しており、PHP/Java/SQLを用いた改修にも携わっております。\n\n"
    "これまでに、某官公庁システムの情報漏洩対策（SKYSEA Client View）の構築・試験（単体／連携／総合試験）、某コンビニ次世代POSシステムの内部結合テスト、スマートフォンアプリのバージョンアップ検証、官公庁向け携帯端末増設の検証など、テスト・検証業務を中心に幅広く経験してまいりました。構築業務ではTeraTermによるSSH接続やiDRACを用いたリモート操作も習得しております。\n\n"
    "開発に携わりたいという思いから、業務後や休日にJava・PHP等の学習（参考書での文法学習、VSCode・Eclipseでの実装）を継続しております。IT業界以前には家電量販店での携帯販売や飲食店での接客・店舗管理の経験があり、コミュニケーション力とユーザー視点も強みです。今後はこれまでの業務経験と自己学習で培った知識を活かし、開発の現場でさらにスキルアップしていきたいと考えております。"
)
data += [C("A23", PR)]

# --- 業務実績表 既存6枠（直近IT案件、新しい順）---
# marks順: AB要件 AC基本 AD詳細 AE製造 AF単体 AG結合 AH総合 AI運用
slot_base = {1: 32, 2: 43, 3: 54, 4: 65, 5: 76, 6: 87}
projects = [
    dict(
        ji="2025.7",
        shi="2026.6",
        goukei="1年",
        gyoshu="IT",
        marks=["", "", "", "", "●", "", "", "●"],
        gengo="PHP / Java / SQL",
        dbos="Windows / Linux",
        fw="Backlog / TeraTerm / WinSCP / WinMerge / Teams / A5:SQL Mk-2",
        hosoku="教務システムの運用保守\n・問合せ対応（ヘルプデスクからのエスカレ対応／仕様と不具合の切り分け／データ補正・SQL修正）\n・不具合対応（不具合チケットの起票／テスト：テスト項目書作成・テスト実施・エビデンス作成）\n・その他（要件定義用の補助資料作成／マニュアル修正）",
    ),
    dict(
        ji="2024.7",
        shi="2025.6",
        goukei="1年",
        gyoshu="IT",
        marks=["", "", "", "", "", "", "●", ""],
        gengo="",
        dbos="Windows / Android / iOS",
        fw="Slack / Backlog / Excel",
        hosoku="既存スマホアプリのバージョンアップ等に伴うアプリ検証作業\n・試験実施（アプリ／OSのバージョンアップに伴う検証試験）\n・設計（サービス終了・改修確認に伴うテスト項目書の作成／汎用テスト項目書の修正）\n・不具合起票（試験中に発見した不具合の比較検証／Backlogでのチケット発行）",
    ),
    dict(
        ji="2024.3",
        shi="2024.6",
        goukei="4ヶ月",
        gyoshu="IT",
        marks=["", "", "", "", "●", "●", "●", ""],
        gengo="",
        dbos="Windows / Linux",
        fw="SKYSEA Client View / Excel / Word / TeraTerm",
        hosoku="某官公庁システムの更改に伴う情報漏洩機能の構築・試験作業\n・SKYSEA Client Viewのインストール（手順書に基づき対象サーバへエージェント導入）\n・設定作業（管理機の設定／端末ポリシー作成・設定：デバイス制限等）\n・各種試験（単体試験・連携試験・総合試験の実施／試験ドキュメント修正）",
    ),
    dict(
        ji="2023.10",
        shi="2024.2",
        goukei="5ヶ月",
        gyoshu="IT",
        marks=["", "", "", "", "", "", "●", ""],
        gengo="",
        dbos="Windows / Android",
        fw="Excel / PowerPoint / Outlook / Teams / OBS Studio",
        hosoku="某官公庁用携帯端末の増設にかかる手順書作成・検証作業\n・手順書作成（番号移行／操作手順／初期設定／キッティング等）\n・検証試験（新旧端末のOS差異による動作検証／専用アプリの動作確認／Android OSバージョンアップ作業の検証）\n・問合せ対応（番号移行に伴う電話・メール対応）",
    ),
    dict(
        ji="2023.2",
        shi="2023.9",
        goukei="8ヶ月",
        gyoshu="IT",
        marks=["", "", "", "", "", "●", "●", ""],
        gengo="",
        dbos="Windows / Android",
        fw="VirtualBox / Eclipse / SQL Mk-2 / VSCode / サクラエディタ / Excel / Outlook / Teams",
        hosoku="某コンビニの次世代POSシステムのテスト業務\n・テスト環境準備（機器初期設定／IP設定／シミュレータ準備：VirtualBox・Eclipse）\n・テストデータ作成（DB編集：SQL Mk-2／バーコード作成／自動化バッチ作成：adbコマンド）\n・シナリオ作成（Excel：VLOOKUP/COUNTIF/IF等）\n・テスト実行（正常系/異常系：異常バーコード・電断・性能等の内部結合テスト）\n・不具合報告・修正確認（障害表作成／売上情報ファイル(json)の期待値確認／確認ツール改修）",
    ),
    dict(
        ji="2020.7",
        shi="2023.1",
        goukei="2年7ヶ月",
        gyoshu="情報通信",
        marks=["", "", "", "", "", "", "", ""],
        gengo="",
        dbos="Windows",
        fw="Excel / Word / PowerPoint / Sales Cloud / Outlook / Teams",
        hosoku="某データセンターのサーバラックレンタル事業（IT事務）\n・レンタル費用の見積もり対応\n・Salesforce(Sales Cloud)登録業務（見積ごとのID発行・費用入力／レポート出力と請求費用の差異確認）\n・請求処理（請求書発行／Sales Cloud登録額との一致確認）\n・その他（顧客案内文・説明会資料作成／チーム内会議／顧客打合せ枠作成）",
    ),
]
MARK_COLS = ["AB", "AC", "AD", "AE", "AF", "AG", "AH", "AI"]
for i, p in enumerate(projects, 1):
    B = slot_base[i]
    data.append(C(f"C{B + 3}", p["ji"]))
    data.append(C(f"C{B + 5}", p["shi"]))
    data.append(C(f"C{B + 7}", p["goukei"]))
    data.append(C(f"I{B}", p["hosoku"]))
    data.append(C(f"X{B + 5}", p["gyoshu"]))
    data.append(C(f"AJ{B + 5}", p["gengo"]))
    data.append(C(f"AM{B + 5}", p["dbos"]))
    data.append(C(f"AP{B + 5}", p["fw"]))
    for col, mk in zip(MARK_COLS, p["marks"]):
        data.append(C(f"{col}{B + 5}", mk))

print(f"writing {len(data)} cells ...", flush=True)
ws.batch_update(data, value_input_option="RAW")
print("[STEP A WRITE OK]", flush=True)

# --- 検証 ---
import time

time.sleep(1)
from gspread.utils import a1_to_rowcol

vals = ws.get_all_values()


def g(a1):
    r, c = a1_to_rowcol(a1)
    try:
        return vals[r - 1][c - 1]
    except:
        return "∅"


print("DB:", g("P18"), g("S18"), "/", g("P19"), g("S19"), flush=True)
print("工程 単体/結合/総合/運用:", g("AN14"), g("AN15"), g("AN16"), g("AN17"), flush=True)
print("PR冒頭:", repr(g("A23")[:48]), flush=True)
for i in [1, 2, 3, 4, 5, 6]:
    B = slot_base[i]
    marks = "".join("●" if g(f"{c}{B + 5}") == "●" else "_" for c in MARK_COLS)
    print(
        f"slot{i}: {g(f'C{B + 3}')}~{g(f'C{B + 5}')}({g(f'C{B + 7}')}) 業種={g(f'X{B + 5}')} marks[要基詳製単結総運]={marks} 言語={g(f'AJ{B + 5}')[:18]} OS={g(f'AM{B + 5}')[:18]}",
        flush=True,
    )
print("[DONE]", flush=True)
