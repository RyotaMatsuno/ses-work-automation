import datetime
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8")

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py"

# バックアップ
bak = path + f".bak_{datetime.date.today().strftime('%m%d')}_jobz"
shutil.copy(path, bak)
print(f"Backup: {bak}")

with open(path, encoding="utf-8") as f:
    content = f.read()

# L805-L806 の affiliation ブロックの後に、
# affiliation が空の場合は input_source（松野LINE/岡本LINE）を所属会社名にフォールバック
# パッチ: L806の直後に else 節を追加

OLD = """    if info.get("affiliation"):
        props["\u6240\u5c5e\u4f1a\u793e"] = {"rich_text": [{"text": {"content": info["affiliation"][:500]}}]}"""

NEW = """    if info.get("affiliation"):
        props["\u6240\u5c5e\u4f1a\u793e"] = {"rich_text": [{"text": {"content": info["affiliation"][:500]}}]}
    else:
        # LINE\u767b\u9332\u306f\u6240\u5c5e\u60c5\u5831\u304c\u306a\u3044\u5834\u5408\u3001\u30bd\u30fc\u30b9\u540d\uff08\u677e\u91ccLINE/\u5ca1\u672cLINE\uff09\u3092\u6240\u5c5e\u4f1a\u793e\u540d\u306b\u5165\u308c\u308b
        _src = get_line_source_label(user_id) or ("\u5ca1\u672cLINE" if sender == "okamoto" else "\u677e\u91ccLINE")
        props["\u6240\u5c5e\u4f1a\u793e"] = {"rich_text": [{"text": {"content": _src}}]}"""

if OLD in content:
    content = content.replace(OLD, NEW)
    print("PATCHED: affiliation fallback to LINE source")
else:
    print("NOT FOUND - checking actual content...")
    # 実際のコード確認
    idx = content.find('info.get("affiliation")')
    if idx >= 0:
        print(repr(content[idx - 10 : idx + 200]))

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

# 確認
with open(path, encoding="utf-8") as f:
    lines = f.readlines()
print("\n=== L803-L825 after patch ===")
for i in range(802, 825):
    if i < len(lines):
        print(f"L{i + 1}: {lines[i]}", end="")
