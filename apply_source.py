import io
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

paths = [
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py",
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py",
]

for path in paths:
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()

    fname = "/".join(path.split("\\")[-2:])

    # ── 修正1: PROP_INPUT_SRC 定数追加 ────────────────────────────
    # PROP_AFFIL の後ろに追加
    OLD_AFFIL_LINE = (
        'PROP_AFFIL     = bytes.fromhex("e68980e5b19ee4bc9ae7a4be").decode()        # \u6240\u5c5e\u4f1a\u793e'
    )
    NEW_AFFIL_LINE = (
        'PROP_AFFIL     = bytes.fromhex("e68980e5b19ee4bc9ae7a4be").decode()        # \u6240\u5c5e\u4f1a\u793e\n'
        'PROP_INPUT_SRC = bytes.fromhex("e585a5e58a9be58583").decode()              # \u5165\u529b\u5143'
    )
    if OLD_AFFIL_LINE in src:
        src = src.replace(OLD_AFFIL_LINE, NEW_AFFIL_LINE, 1)
        print(f"✅ {fname}: PROP_INPUT_SRC追加")
    elif "PROP_INPUT_SRC" in src:
        print(f"⚠️  {fname}: PROP_INPUT_SRC既存")
    else:
        print(f"❌ {fname}: PROP_AFFIL行が見つからない")

    # ── 修正2: _engineer_source + _case_source 関数追加 ───────────
    # _affil_contact の直前に追加
    NEW_FUNCS = r'''
def _engineer_source(engineer: dict) -> str:
    """誰がやり取りしているか（入力元フィールド or 備考から判定）"""
    src = _select_prop(engineer, PROP_INPUT_SRC)
    if src:
        return src
    memo = _text_prop(engineer, PROP_MEMO)
    if not memo:
        return ""
    if "[LINE auto-register: matsuno]" in memo:
        return "\u677e\u91ceLINE"
    if "[LINE auto-register: okamoto]" in memo:
        return "\u5ca1\u672cLINE"
    if "[\u81ea\u52d5\u53d6\u8fbc]" in memo or "[automail" in memo.lower():
        return "\u30e1\u30fc\u30eb"
    return ""


def _case_source(project: dict) -> str:
    """どこから来た案件か（入力元フィールド）"""
    return _select_prop(project, PROP_INPUT_SRC)

'''
    insert_at = src.find("\ndef _affil_contact(")
    if insert_at >= 0:
        src = src[:insert_at] + NEW_FUNCS + src[insert_at:]
        print(f"✅ {fname}: _engineer_source/_case_source追加")
    else:
        print(f"❌ {fname}: _affil_contact位置が見つからない")

    # ── 修正3: format_project_result のヘッダーと案件行を更新 ──────
    # ヘッダー行に 人員の送信元を追加
    OLD_HEADER = '    lines = [f"\\u3010{initial}\\uff5c{station}\\u3011\\u30de\\u30c3\\u30c1\\u6848\\u4ef6 {len(projects)}\\u4ef6"]'
    NEW_HEADER = (
        '    lines = [f"\\u3010{initial}\\uff5c{station}\\u3011\\u30de\\u30c3\\u30c1\\u6848\\u4ef6 {len(projects)}\\u4ef6"]\n'
        "    _esrc = _engineer_source(engineer)\n"
        "    if _esrc:\n"
        '        lines.append(f"\\u6765\\u6e90: {_esrc}")  # \u6765\u6e90:'
    )
    if OLD_HEADER in src:
        src = src.replace(OLD_HEADER, NEW_HEADER, 1)
        print(f"✅ {fname}: ヘッダー来源行追加")
    else:
        print(f"❌ {fname}: ヘッダーパターン不一致")

    # 案件行に 送信元を追加（locの行の後ろ）
    OLD_CASE_LINE = '            f"  {loc}" + (f" ({remote})" if remote else "") + (f" / {period}" if period else "") + f" [{age}\\u65e5\\u524d]",'
    NEW_CASE_LINE = (
        '            f"  {loc}" + (f" ({remote})" if remote else "") + (f" / {period}" if period else "") + f" [{age}\\u65e5\\u524d]",\n'
        '            (f"  \\u9001\\u4fe1\\u5143: {_case_source(pj)}" if _case_source(pj) else ""),  # \u9001\u4fe1\u5143:'
    )
    if OLD_CASE_LINE in src:
        src = src.replace(OLD_CASE_LINE, NEW_CASE_LINE, 1)
        print(f"✅ {fname}: 案件送信元行追加")
    else:
        print(f"❌ {fname}: 案件行パターン不一致")
        for i, line in enumerate(src.split("\n"), 1):
            if "loc" in line and "remote" in line and "日前" in line:
                print(f"  現在L{i}: {repr(line.strip()[:80])}")

    with open(path, "w", encoding="utf-8") as f:
        f.write(src)

    r = subprocess.run(["python", "-m", "py_compile", path], capture_output=True, text=True)
    print(f"{'✅' if r.returncode == 0 else '❌'} {fname}: 構文{'OK' if r.returncode == 0 else r.stderr[:80]}")
    print()
