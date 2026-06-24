# -*- coding: utf-8 -*-
# line_query.py の変更内容：
# 1. format_project_result: 概要を「連絡先のみ」に変更（業務内容テキストなし）
# 2. 「詳細 ①」コマンドに対応する detail_query 関数を追加
# 3. handle_line_query で「詳細 N」パターンを検出して detail_query を呼ぶ
# 4. 詳細表示は案件の全フィールド+概要全文を1通で返す

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

# ========== 変更1: format_project_result の detail表示を連絡先のみに ==========
# 現在: raw_detail 全文を概要として表示
# 変更後: メアド・電話番号・担当者名だけ抽出して「連絡先:」として表示

old1 = """        if raw_detail:
            # 概要全文表示（文字数制限なし）
            lines.append(f"  概要: {raw_detail}")"""

new1 = """        # 連絡先のみ抽出（メアド・電話・担当者名）
        _contact = _extract_contacts(raw_detail)
        if _contact:
            lines.append(f"  連絡先: {_contact}")"""

if old1 in content:
    content = content.replace(old1, new1)
    print("変更1 OK", flush=True)
else:
    print("変更1 MISS - 別パターン検索", flush=True)
    idx = content.find("raw_detail")
    while idx >= 0:
        print(repr(content[max(0, idx - 20) : idx + 100]), flush=True)
        idx = content.find("raw_detail", idx + 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("変更1 書き込み完了", flush=True)
