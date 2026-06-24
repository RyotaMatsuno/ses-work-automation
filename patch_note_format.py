import sys

sys.stdout.reconfigure(encoding="utf-8")

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\mail_pipeline.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

# バックアップ
import datetime
import shutil

bak = path + f".bak_{datetime.date.today().strftime('%m%d')}_jobz"
shutil.copy(path, bak)
print(f"Backup: {bak}")

# L885: note のフォーマットを "送信者:" -> "送信元:" に変更
# また "[自動取込] 件名: xxx\n送信元: yyy\n受信日: zzz" の形式に統一
# （既存の備考（LINEメモ）と同じフォーマットにする）

OLD = "    note = f\"【メールから自動登録】\\n送信者: {sender}\\n件名: {subject}\\n\\n{info.get('note','')}\""
NEW = "    note = f\"[自動取込] 件名: {subject}\\n送信元: {sender}\\n\\n{info.get('note','')}\""

if OLD in content:
    content = content.replace(OLD, NEW)
    print("PATCHED: note format (register_engineer)")
else:
    print("NOT FOUND: trying alternative search...")
    # 前後の文脈で探す
    lines = content.split("\n")
    for i, line in enumerate(lines, 1):
        if "送信者" in line and "note" in line and "register_engineer" not in line:
            print(f"  L{i}: {line.strip()!r}")

# register_project の note も同じ問題があるか確認・修正
OLD_PROJ = (
    "    note = f\"【メールから自動登録】\\n送信者: {sender}\\n件名: {subject}\\n\\n{raw_body or info.get('note','')}\""
)
NEW_PROJ = "    note = f\"[自動取込] 件名: {subject}\\n送信元: {sender}\\n\\n{raw_body or info.get('note','')}\""

if OLD_PROJ in content:
    content = content.replace(OLD_PROJ, NEW_PROJ)
    print("PATCHED: note format (register_project)")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("File written.")

# 確認
with open(path, encoding="utf-8") as f:
    lines = f.readlines()
print("\n=== L882-L892 after patch ===")
for i in range(881, 892):
    print(f"L{i + 1}: {lines[i]}", end="")
