import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# === 診断2: H.SのNotionレコードの完全な状態と、なぜマッチしないかを特定 ===

import re

# H.Sのレコードの実態
engineer_hs = {
    "名前": "H.S",
    "イニシャル": "",  # 空！
    "最寄り駅": "",  # 空！
    "備考（LINEメモ）": "[LINE auto-register: matsuno]\n55-year-old male...",
    "スキル": ["Java", "JavaScript", "SQL Server", "Oracle", "Spring", "C#"],
    "単価（万円）": 70.0,
    "稼働状況": "稼働可能",
}

print("=== H.Sのレコード状態 ===")
print(f"名前: [{engineer_hs['名前']}]")
print(f"イニシャル: [{engineer_hs['イニシャル']}] ← 空！")
print(f"最寄り駅: [{engineer_hs['最寄り駅']}] ← 空！")
print(f"備考: [{engineer_hs['備考（LINEメモ）'][:60]}...]")
print()


# _normalize_initial のシミュレーション
def _normalize_initial(s):
    return re.sub(r"[\s\u3000.\u30fb\u00b7]", "", s).upper()


# _match_initial のシミュレーション
def _match_initial(engineer, initial):
    ini = engineer.get("イニシャル", "")
    if ini:
        result = _normalize_initial(ini) == initial.upper()
        print(f"  イニシャルフィールドあり: normalize({ini})={_normalize_initial(ini)} == {initial.upper()} → {result}")
        return result
    name = engineer.get("名前", "")
    result = _normalize_initial(name) == initial.upper()
    print(
        f"  イニシャルフィールドなし → 名前から: normalize({name})={_normalize_initial(name)} == {initial.upper()} → {result}"
    )
    return result


# _match_station のシミュレーション
def _match_station(engineer, station):
    if not station:
        return True
    sta = engineer.get("最寄り駅", "")
    if sta:
        result = station in sta
        print(f"  最寄り駅フィールドあり: {station} in {sta} → {result}")
        return result
    memo = engineer.get("備考（LINEメモ）", "")
    if memo and station in memo:
        print(f"  メモで発見: {station} in memo → True")
        return True
    print("  駅データなし → True (initial-only match)")
    return True  # no station data


print("=== LINEで「HS 北小金」を送ったときの処理 ===")
print()

# classify_query
text = "HS 北小金"
match = re.match(r"^([A-Za-z]{1,4})[\s\u3000/](.+)$", text.strip())
if match:
    initial = match.group(1).upper()
    station = match.group(2).strip()
    print(f"classify_query: type=engineer, initial={initial}, station={station}")
else:
    print("classify_query: type=project ← ここで既に間違い!")

print()
print("=== _match_initial チェック ===")
result_ini = _match_initial(engineer_hs, initial)
print(f"→ _match_initial: {result_ini}")
print()
print("=== _match_station チェック ===")
result_sta = _match_station(engineer_hs, station)
print(f"→ _match_station: {result_sta}")
print()
print(f"=== 最終マッチ判定: {result_ini and result_sta} ===")
print()

# 本番テストで「一致する案件が見つかりませんでした」が返ったということは
# engineer_queryは成功してH.Sを見つけたが、案件側でマッチしなかった
print("=== 問題の真相 ===")
print("H.S自体はイニシャルマッチ(H.S→HS)と駅データなし→True で検索できる")
print("「一致する案件が見つかりませんでした」は project_query の返答")
print("つまり: LINEに送られたメッセージが engineer クエリではなく project クエリとして処理された可能性")
print()
print("=== 元のLINEメッセージ確認 ===")
original = """おつかれさまです!
現在、5月から阿部氏の案件でお世話になっていた
うちの社員の林が、案件的に元々スポットの可能性もあるってことで
入ってまして、7月から後続案件があって、受注しているけど
開始時期が6月2週目に入らないと分からないって言われたので
今日からまた営業再開することになりました、、、
Web系のJAVA案件ありましたらお願いします!
長期案件、リモート併用希望です。
通いは1時間程度まで大丈夫です。
※リモートもあれば嬉しいけど、常駐も全然相談ください。
よろしくお願いします!
------------------------------
【名 前】H.S(55歳/男性)※業界経験26年
【最寄駅】北小金駅(千代田線)※リモート希望、併用可
【稼 働】7月~
【所 属】弊社正社員
【単 金】70万(140-180h) 
【スキル】Java、PL/SQL、JavaScript、SQLServer、Oracle、Spring、C#等
     基本設計~製造~運用・保守
【並 行】本日から営業開始"""

print(f"文字数: {len(original.strip())}文字 ← 50文字ガードに引っかかる！！")
print()
print("現在のhandle_line_query:")
print("  if len(text.strip()) > 50: return None  ← これでNoneが返る")
print("  → Noneなのでwebhook_server.pyがどう処理するか？")
print()
print("=== 根本原因: Noneが返った後、webhook_server.pyが")
print("    「一致する案件が見つかりませんでした」を付けてそのまま返信している ===")
