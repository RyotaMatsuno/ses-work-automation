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

    # ── 修正1: _clean_detail を置き換え ────────────────────────────
    start = src.find("def _clean_detail(")
    end = src.find("\ndef engineer_query(", start)
    if start < 0 or end < 0:
        print(f"❌ {fname}: _clean_detail 位置特定失敗 start={start} end={end}")
        continue

    NEW_CLEAN = r'''def _clean_detail(text: str, max_len: int = 250) -> str:
    """
    デュアル抽出:
    Phase1: メール/電話/担当者名を全文から直接抽出（送信者行は除外）
    Phase2: 業務内容マーカー以降のテキストを抽出
    表示: [連絡先] | [業務内容]  or どちらか一方
    """
    if not text:
        return ""
    _SKIP = ("\u9001\u4fe1\u8005:", "\u4ef6\u540d:", "Subject:", "From:", "[LINE auto-register")
    _EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
    _PHONE_RE = re.compile(r'0[0-9]{1,4}[\-\s]?[0-9]{3,4}[\-\s]?[0-9]{4}')
    _CTCT_RE  = re.compile(r'^\u62c5\u5f53[^\u8005\u304c]{0,3}[\uff1a:]\s*\S')
    contacts: list[str] = []
    for _ln in text.split("\n"):
        _s = _ln.strip()
        if not _s:
            continue
        if any(_s.startswith(_p) for _p in _SKIP):
            continue
        if _CTCT_RE.match(_s) and len(_s) < 25 and _s not in contacts:
            contacts.append(_s)
        _em = _EMAIL_RE.search(_s)
        if _em and _em.group(0) not in contacts:
            contacts.append(_em.group(0))
        _ph = _PHONE_RE.search(_s)
        if _ph and len(_s) <= 20 and _ph.group(0) not in contacts:
            contacts.append(_ph.group(0))
        if len(contacts) >= 3:
            break
    _MARKERS = [
        "\u3010\u696d\u52d9\u5185\u5bb9\u3011",
        "\u3010\u4f5c\u696d\u5185\u5bb9\u3011",
        "\u3010\u696d\u52d9\u6982\u8981\u3011",
        "\u696d\u52d9\u5185\u5bb9\uff1a",
        "\u696d\u52d9\u5185\u5bb9:",
        "\u300a\u696d\u52d9\u5185\u5bb9\u300b",
        "\u25a0\u696d\u52d9\u5185\u5bb9",
        "\u25a0\u4f5c\u696d\u5185\u5bb9",
        "\u3010\u6848\u4ef6\u3011",
        "\u3010\u6982\u8981\u3011",
        "\u25c6 \u6848\u4ef6\u540d\uff1a",
        "\u25c6\u6848\u4ef6\u540d\uff1a",
        "\u25a0\u6848\u4ef6\u540d\uff1a",
        "\u25c6 \u6848\u4ef6\u540d",
        "\u25c6 \u30b9\u30ad\u30eb",
    ]
    content = ""
    for _mk in _MARKERS:
        _idx = text.find(_mk)
        if _idx >= 0:
            content = re.sub(r"\n+", " ", text[_idx:]).strip()
            break
    contact_str = " / ".join(contacts)
    if contact_str and content:
        _av = max_len - len(contact_str) - 3
        result = (contact_str + " | " + content[:_av]) if _av >= 40 else contact_str
    elif contact_str:
        result = contact_str
    elif content:
        result = content
    else:
        result = re.sub(r"\n+", " ", text).strip()
    result = re.sub(r"\s+", " ", result).strip()
    return (result[:max_len] + "...") if len(result) > max_len else result

'''

    src = src[:start] + NEW_CLEAN + src[end:]
    print(f"✅ {fname}: _clean_detail置換")

    # ── 修正2: remote空欄の "()" を除去 ────────────────────────────
    OLD_LOC = 'f"  {loc}({remote})"'
    NEW_LOC = 'f"  {loc}" + (f" ({remote})" if remote else "")'
    if OLD_LOC in src:
        src = src.replace(OLD_LOC, NEW_LOC, 1)
        print(f"✅ {fname}: remote空欄BUG修正")
    else:
        # 現在の loc 行を確認
        for i, line in enumerate(src.split("\n"), 1):
            if "loc" in line and "remote" in line and "format" not in line and "PROP" not in line:
                print(f"  L{i}: {line.strip()[:70]}")

    with open(path, "w", encoding="utf-8") as f:
        f.write(src)

    r = subprocess.run(["python", "-m", "py_compile", path], capture_output=True, text=True)
    print(f"{'✅' if r.returncode == 0 else '❌'} {fname}: 構文{'OK' if r.returncode == 0 else r.stderr[:80]}")
    print()
