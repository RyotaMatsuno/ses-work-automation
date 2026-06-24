import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.getcwd())
import sheets_reader as SR

ss = SR._open()


def gv(row, i):
    return row[i].strip() if i < len(row) and row[i] else ""


print("################ TERRA (status[2] 区分[1] サイト[8] 名[3] 単価[7] 仕入[13] 案件[6]) ################")
data = ss.worksheet("TERRA").get_all_values()
for row in data[4:]:
    name = gv(row, 3)
    if not name or name in ("氏名", "稼働中合計"):
        continue
    print(
        f"  st={gv(row, 2):<8} 区分={gv(row, 1):<3} site={gv(row, 8):<4} {name:<10} 単価={gv(row, 7):<8} 仕入={gv(row, 13):<8} 案件={gv(row, 6)[:14]} 担当={gv(row, 0)}"
    )

print("################ フラップテック (status[1] 担当[0] サイト[12] 名[2] 単価[6] 仕入[7]) ################")
data = ss.worksheet("フラップテック").get_all_values()
for row in data[3:]:
    name = gv(row, 2)
    if not name or name in ("氏名",):
        continue
    print(
        f"  st={gv(row, 1):<10} 担当={gv(row, 0):<6} site={gv(row, 12):<4} {name:<10} 単価={gv(row, 6):<8} 仕入={gv(row, 7):<8}"
    )

print("################ グレイスライン (status[0] サイト[10] 名[1] 単価[5] 仕入[6]) ################")
data = ss.worksheet("グレイスライン").get_all_values()
for row in data[3:]:
    name = gv(row, 1)
    if not name or name in ("氏名",):
        continue
    print(f"  st={gv(row, 0):<10} site={gv(row, 10):<4} {name:<10} 単価={gv(row, 5):<8} 仕入={gv(row, 6):<8}")
