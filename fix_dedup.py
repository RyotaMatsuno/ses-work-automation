import io
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

# 修正1: 単価上限を150万に（SES月額の現実的な上限）
OLD_CAP = """            # 単価が200万超は時給/年額等の異常データとして除外
            if budget > 200:
                continue"""
NEW_CAP = """            # 単価が150万超は時給/年額等の異常データとして除外（SES月額上限）
            if budget > 150:
                continue"""

if OLD_CAP in src:
    src = src.replace(OLD_CAP, NEW_CAP, 1)
    print("✅ 上限 200→150万 OK")

# 修正2: dedup が案件名の先頭30文字でしか比較していないことを確認
# 現在: _text_prop(_p, PROP_PJNAME) で全文比較している
# 「Java×AI_デジタル通貨・ブロックチェーン企業」と「Java×AI_デジタル通貨・ブロックチェーン企」
# → 末尾が違うので重複と判定されていない

# dedup を先頭40文字でグルーピングするように変更
OLD_DEDUP = """    # dedup by project name
    _seen: set[str] = set()
    _deduped: list[dict] = []
    for _p in projects:
        _k = _text_prop(_p, PROP_PJNAME)
        if _k and _k not in _seen:
            _seen.add(_k)
            _deduped.append(_p)
    projects = _deduped"""

NEW_DEDUP = """    # dedup by project name (先頭40文字で重複判定)
    _seen: set[str] = set()
    _deduped: list[dict] = []
    for _p in projects:
        _k = _text_prop(_p, PROP_PJNAME)
        _k40 = _k[:40] if _k else ""
        if _k40 and _k40 not in _seen:
            _seen.add(_k40)
            _deduped.append(_p)
    projects = _deduped"""

if OLD_DEDUP in src:
    src = src.replace(OLD_DEDUP, NEW_DEDUP, 1)
    print("✅ dedup: 先頭40文字重複排除 OK")
else:
    print("❌ dedup パターン不一致")
    idx = src.find("# dedup")
    print(repr(src[idx : idx + 300]))

with open(path, "w", encoding="utf-8") as f:
    f.write(src)

path2 = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py"
with open(path2, "r", encoding="utf-8") as f:
    s2 = f.read()
for old, new in [(OLD_CAP, NEW_CAP), (OLD_DEDUP, NEW_DEDUP)]:
    if old in s2:
        s2 = s2.replace(old, new, 1)
with open(path2, "w", encoding="utf-8") as f:
    f.write(s2)

for p in [path, path2]:
    r = subprocess.run(["python", "-m", "py_compile", p], capture_output=True, text=True)
    fname = "/".join(p.split("\\")[-2:])
    print(f"{'✅' if r.returncode == 0 else '❌'} {fname}: 構文{'OK' if r.returncode == 0 else r.stderr}")
