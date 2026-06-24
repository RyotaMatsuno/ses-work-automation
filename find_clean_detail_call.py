# -*- coding: utf-8 -*-
# _clean_detail を完全削除して生テキストをそのまま返す形に変更
path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

# format_project_result の detail表示部分を確認
idx = content.find("detail   = _clean_detail")
if idx < 0:
    idx = content.find("_clean_detail(")
print(f"_clean_detail呼び出し位置: {idx}", flush=True)
print(content[max(0, idx - 50) : idx + 100], flush=True)
