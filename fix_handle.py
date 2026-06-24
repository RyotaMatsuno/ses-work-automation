import io
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

paths = [
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py",
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py",
]

NEW_HANDLE = '''def handle_line_query(text: str) -> str | None:
    """
    LINE照会クエリ処理。
    - 「HS 北小金」「TK 渋谷」「案件名」等の短いクエリ → マッチ結果文字列
    - マッチなし / スキルシート本文 / 長文 / 空文字 → None (次の処理に委ねる)
    """
    if not text or not text.strip():
        return None
    # 100文字超はスキルシート本文・長文メッセージ → スルー
    if len(text.strip()) > 100:
        return None
    try:
        query_type, params = classify_query(text)
        if query_type == "engineer":
            result = engineer_query(params["initial"], params["station"])
        else:
            result = project_query(params["name"])
        # 一致なし の場合は None を返してprocess_messageに委ねる
        if result and (
            "\\u4e00\\u81f4\\u3059\\u308b\\u4eba\\u54e1\\u304c\\u898b\\u3064\\u304b\\u308a\\u307e\\u305b\\u3093" in result or
            "\\u4e00\\u81f4\\u3059\\u308b\\u6848\\u4ef6\\u304c\\u898b\\u3064\\u304b\\u308a\\u307e\\u305b\\u3093" in result
        ):
            return None
        return result if result else None
    except Exception:
        logger.exception("line_query failed")
        return None  # エラー時も None → 通常フローに委ねる
'''

for path in paths:
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()

    old_start = src.find("def handle_line_query")
    old_end = src.find("\ndef _prop(", old_start)
    if old_start < 0 or old_end < 0:
        print(f"❌ パターン不一致: {path}")
        continue

    src = src[:old_start] + NEW_HANDLE + "\n\n" + src[old_end:]

    with open(path, "w", encoding="utf-8") as f:
        f.write(src)

    r = subprocess.run(["python", "-m", "py_compile", path], capture_output=True, text=True)
    fname = "/".join(path.split("\\")[-2:])
    if r.returncode == 0:
        print(f"✅ {fname}: 構文OK")
    else:
        print(f"❌ {fname}: {r.stderr[:200]}")
