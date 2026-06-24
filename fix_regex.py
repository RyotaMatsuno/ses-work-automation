# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LQ = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
content = open(LQ, encoding="utf-8").read()

# 化けた正規表現を修正（ASCII文字のみの安全な書き方に変更）
OLD_NORM = r"""        _k_norm = _re_dedup.sub(r'[、。・，．　\s【】（）()「」『』]', '', _k)[:30] if _k else \"\""""
# 実際のファイル内容を確認してから差し替え
idx = content.find("_k_norm = ")
if idx >= 0:
    line_end = content.find("\n", idx)
    old_line = content[idx:line_end]
    print(f"現在の行: {repr(old_line)}")

    # 安全な書き方（unicodeエスケープ使用）
    new_line = "        _k_norm = _re_dedup.sub(r'[\\u3001\\u3002\\u30fb\\uff0c\\uff0e\\u3000\\s\\u3010\\u3011\\uff08\\uff09()\\u300c\\u300d\\u300e\\u300f]', '', _k)[:30] if _k else \"\""
    content = content[:idx] + new_line + content[line_end:]
    open(LQ, "w", encoding="utf-8").write(content)
    print("正規表現修正OK")
else:
    print("_k_normが見つかりません")
