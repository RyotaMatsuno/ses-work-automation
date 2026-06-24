import io
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

paths = [
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py",
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py",
]

# ── 追加する _affil_contact 関数 ────────────────────────────────
NEW_FUNC = r'''
def _affil_contact(engineer: dict) -> str | None:
    """所属連絡先を返す（空なら None）
    優先順: PROP_AFFIL(日本語) > 備考の送信元 > 手動登録弊社社員 > None
    """
    affil      = _text_prop(engineer, PROP_AFFIL)
    affil_cont = _text_prop(engineer, PROP_AFFIL_CONT)
    affil_mail = _text_prop(engineer, PROP_AFFIL_MAIL)
    memo       = _text_prop(engineer, PROP_MEMO)

    # 1. 有効な日本語所属データ
    if affil and any("\u4e00" <= c <= "\u9fff" or "\u3040" <= c <= "\u30ff" for c in affil):
        parts = [p for p in [affil, affil_cont, affil_mail] if p]
        return " / ".join(parts) if parts else None

    if not memo:
        return None

    # 2. 手動登録の自社社員
    if "\u624b\u52d5\u767b\u9332" in memo and "\u5f0a\u793e\u793e\u54e1" in memo:
        return "\u81ea\u793e\u793e\u54e1"

    # 3. 自動取込メール → 送信元から抽出
    _EMAIL_RE2  = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
    _SENDER_RE2 = re.compile(
        r"(?:\u9001\u4fe1\u5143|\u9001\u4fe1\u8005)[:\s\uff1a]+(.{1,80}?)"
        r"(?:\s*/\s*\u53d7\u4fe1\u65e5|$)",
        re.DOTALL,
    )
    _m = _SENDER_RE2.search(memo)
    if _m:
        raw = _m.group(1).strip()
        _em = _EMAIL_RE2.search(raw)
        if _em:
            email = _em.group(0)
            before = re.sub(r"^[<\s]+|[>\s]+$", "", raw[: raw.find(email)]).strip()
            parts = [p for p in [before, email] if p]
            return " / ".join(parts[:2])
        return raw[:40] if raw else None

    return None

'''

for path in paths:
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()

    fname = "/".join(path.split("\\")[-2:])

    # _affil_contact を _clean_detail の前に挿入
    insert_at = src.find("\ndef _clean_detail(")
    if insert_at < 0:
        print(f"❌ {fname}: _clean_detail 位置が見つからない")
        continue
    src = src[:insert_at] + NEW_FUNC + src[insert_at:]
    print(f"✅ {fname}: _affil_contact 追加")

    # format_project_result の 所属行を _affil_contact() に差し替え
    # 現在: affil_parts = [p for p in [affil, affil_cont, affil_mail] if p]
    #        if affil_parts:
    #            lines.append(f"\u6240\u5c5e: " + " / ".join(affil_parts))
    OLD_AFFIL_DISP = (
        "    # \u6240\u5c5e\u60c5\u5831\u30e9\u30a4\u30f3\uff08\u610f\u5411\u78ba\u8a8d\u5148\uff09\n"
        "    affil_parts = [p for p in [affil, affil_cont, affil_mail] if p]\n"
        "    if affil_parts:\n"
        '        lines.append("\\u6240\\u5c5e: " + " / ".join(affil_parts))'
    )
    NEW_AFFIL_DISP = (
        "    # \u6240\u5c5e\u60c5\u5831\u30e9\u30a4\u30f3\uff08\u610f\u5411\u78ba\u8a8d\u5148\uff09\n"
        "    _ac = _affil_contact(engineer)\n"
        "    if _ac:\n"
        '        lines.append("\\u6240\\u5c5e: " + _ac)'
    )

    if OLD_AFFIL_DISP in src:
        src = src.replace(OLD_AFFIL_DISP, NEW_AFFIL_DISP, 1)
        print(f"✅ {fname}: 所属表示を _affil_contact() に差し替え")
    else:
        # 別パターンを探す
        idx = src.find("affil_parts")
        if idx >= 0:
            print(f"  現在の所属行（L付近）: {src[max(0, idx - 30) : idx + 100].replace(chr(10), ' | ')}")
        else:
            print(f"⚠️ {fname}: affil_parts が見つからない → 手動確認")

    # affil, affil_cont, affil_mail の変数定義が不要になるが残しておいても問題なし

    with open(path, "w", encoding="utf-8") as f:
        f.write(src)

    r = subprocess.run(["python", "-m", "py_compile", path], capture_output=True, text=True)
    print(f"{'✅' if r.returncode == 0 else '❌'} {fname}: 構文{'OK' if r.returncode == 0 else r.stderr[:80]}")
    print()
