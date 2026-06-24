# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LQ = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
content = open(LQ, encoding="utf-8").read()

# _k_norm行を完全に差し替え（rawストリング使わずにシンプルに）
idx = content.find("        _k_norm = ")
if idx >= 0:
    line_end = content.find("\n", idx)
    # 句読点除去: re.subで記号類を空文字に
    new_line = "        _k_norm = _re_dedup.sub('[^A-Za-z0-9\\u3040-\\u9fff]', '', _k)[:30] if _k else \"\""
    content = content[:idx] + new_line + content[line_end:]
    open(LQ, "w", encoding="utf-8").write(content)
    print("修正OK")

# 確認
r = __import__("subprocess").run(
    [
        sys.executable,
        "-c",
        "import sys; sys.path.insert(0, r'C:\\Users\\ma_py\\OneDrive\\デスクトップ\\ses_work\\line_webhook'); from line_query import handle_line_query; print('import OK')",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook",
    timeout=10,
)
print(r.stdout.strip() or "ERR: " + r.stderr[:200])
