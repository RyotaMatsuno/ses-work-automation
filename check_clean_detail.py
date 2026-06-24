# -*- coding: utf-8 -*-
path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

# _clean_detail の max_len と format_project_result の detail表示を確認
idx = content.find("def _clean_detail")
end = content.find("\ndef ", idx + 10)
print("=== _clean_detail ===", flush=True)
print(content[idx:end], flush=True)
