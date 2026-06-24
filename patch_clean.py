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

    # ── 修正1: _clean_detail を v3 に置き換え ──────────────────────
    OLD_CLEAN = src[src.find("def _clean_detail") : src.find("\ndef engineer_query")]
    NEW_CLEAN = r'''def _clean_detail(text: str, max_len: int = 250) -> str:
    """案件詳細から業務内容を抽出（マーカー優先 → 挨拶スキップ）"""
    if not text:
        return ""
    # フェーズ1: 業務内容マーカーがあればそこから開始
    markers = [
        r"\u25c6\s*\u696d\u52d9\u5185\u5bb9", r"\u25c6\s*\u4f5c\u696d\u5185\u5bb9",
        r"\u25c6\s*\u6848\u4ef6\u540d",
        r"\u25a0\s*\u696d\u52d9\u5185\u5bb9", r"\u25a0\s*\u4f5c\u696d\u5185\u5bb9",
        r"\u25a0\s*\u6848\u4ef6\u6982\u8981", r"\u25a0\s*\u696d\u52d9\u6982\u8981",
        r"\u3010\u696d\u52d9\u5185\u5bb9\u3011", r"\u3010\u4f5c\u696d\u5185\u5bb9\u3011",
        r"\u3010\u696d\u52d9\u6982\u8981\u3011", r"\u3010\u6848\u4ef6\u6982\u8981\u3011",
        r"\u300a\u696d\u52d9\u5185\u5bb9\u300b", r"\uff1c\u696d\u52d9\u5185\u5bb9\uff1e",
        r"\u25bc\u696d\u52d9\u5185\u5bb9", r"\u30fb\u696d\u52d9\u5185\u5bb9",
        r"\u696d\u52d9\u5185\u5bb9\uff1a", r"\u696d\u52d9\u5185\u5bb9:",
        r"\u4f5c\u696d\u5185\u5bb9\uff1a", r"\u4f5c\u696d\u5185\u5bb9:",
    ]
    for pattern in markers:
        m = re.search(pattern, text)
        if m:
            snippet = re.sub(r"\n+", " ", text[m.start():]).strip()
            return (snippet[:max_len] + "...") if len(snippet) > max_len else snippet
    # フェーズ2: マーカーなし → 挨拶ブロックをスキップして本文を取得
    greet_patterns = [
        r"^\u682a\u5f0f\u4f1a\u793e", r"^\u5408\u540c\u4f1a\u793e",
        r"^\u6709\u9650\u4f1a\u793e", r"^\u4e00\u822c\u793e\u56e3\u6cd5\u4eba",
        r"\u3054\u62c5\u5f53\u8005", r"\u62c5\u5f53\u8005\u69d8",
        r"\u304a\u4e16\u8a71\u306b\u306a\u3063\u3066\u304a\u308a\u307e\u3059",
        r"\u304a\u4e16\u8a71\u306b\u306a\u308a\u307e\u3059",
        r"\u3044\u3064\u3082.*\u304a\u4e16\u8a71", r"\u5927\u5909.*\u304a\u4e16\u8a71",
        r"^BCC", r"^CC", r"^\s*$",
        r"\u8a72\u5f53\u4eba\u6750\u304c\u3044\u3089\u3063\u3057\u3083",
        r"\u898b\u5408\u3046\u65b9\u304c\u3044\u3089\u3063\u3057\u3083",
        r"\u3054\u7d39\u4ecb.*\u304a\u9858\u3044",
        r"\u30a8\u30f3\u30c8\u30ea\u30fc\u3044\u305f\u3060\u3051\u308b",
        r"^---", r"^===", r"^\uff3f\uff3f",
        r"\[LINE auto-register",
        r"\u30e1\u30fc\u30eb\u304b\u3089\u81ea\u52d5\u767b\u9332",
        r"^\u9001\u4fe1\u8005:", r"^\u4ef6\u540d:",
    ]
    lines = text.split("\n")
    content_lines = []
    skipping = True
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if skipping:
            if any(re.search(p, stripped) for p in greet_patterns):
                continue
            skipping = False
        content_lines.append(stripped)
    result = re.sub(r"\s+", " ", " ".join(content_lines)).strip()
    return (result[:max_len] + "...") if len(result) > max_len else result


'''

    if OLD_CLEAN in src:
        src = src.replace(OLD_CLEAN, NEW_CLEAN)
        print(f"✅ {path.split(chr(92))[-1]}: _clean_detail置換OK")
    else:
        print("❌ _clean_detail パターン不一致")
        continue

    # ── 修正2: 担当者空欄の表示を修正 ─────────────────────────────
    # 「/ 担当」ではなく担当者があるときだけ表示
    OLD_ASSIGN = 'f"  \\u5358\\u4fa1: {_format_number(budget)}\\u4e07 / \\u7c97\\u5229: {_format_number(gross)}\\u4e07 / {assignee}\\u62c5\\u5f53",'
    NEW_ASSIGN = 'f"  \\u5358\\u4fa1: {_format_number(budget)}\\u4e07 / \\u7c97\\u5229: {_format_number(gross)}\\u4e07" + (f" / {assignee}\\u62c5\\u5f53" if assignee else ""),'

    if OLD_ASSIGN in src:
        src = src.replace(OLD_ASSIGN, NEW_ASSIGN)
        print(f"✅ {path.split(chr(92))[-1]}: 担当者空欄修正OK")
    else:
        # 別のエスケープ形式かもしれないので実際の行を確認
        for i, line in enumerate(src.split("\n"), 1):
            if "担当" in line and "粗利" in line and "format_number" in line:
                print(f"  L{i}: {line.strip()[:80]}")

    with open(path, "w", encoding="utf-8") as f:
        f.write(src)

    r = subprocess.run(["python", "-m", "py_compile", path], capture_output=True, text=True)
    fname = "/".join(path.split("\\")[-2:])
    print(f"{'✅' if r.returncode == 0 else '❌'} {fname}: 構文{'OK' if r.returncode == 0 else r.stderr[:100]}")
    print()
