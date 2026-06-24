with open("freee/freee_invoice_v2.py", encoding="utf-8") as f:
    c = f.read()

# 組み込む追加コード
insert_code = """
    # ===== 請求書作成完了後: 契約マスターのステータスを自動更新 =====
    if ok > 0:
        try:
            import sys as _sys2
            import os as _os2
            _sys2.path.insert(0, _os2.path.dirname(__file__))
            from auto_status_update import update_status_after_invoice
            invoiced_names = [e["name"] for e in entries]
            print(f"\\n[auto_status] 請求書作成済み人員のステータスを稼働中に更新...")
            update_status_after_invoice(names=invoiced_names)
        except Exception as _e:
            print(f"[auto_status] ステータス更新スキップ（エラー: {_e}）")
"""

# run()の末尾 print("-> https://...") の直後に挿入
old = '    print(f"-> https://secure.freee.co.jp/invoices")\n\nif __name__ == "__main__":'
new = '    print(f"-> https://secure.freee.co.jp/invoices")' + insert_code + '\nif __name__ == "__main__":'

if old in c:
    c2 = c.replace(old, new)
    with open("freee/freee_invoice_v2.py", "w", encoding="utf-8") as f:
        f.write(c2)
    print("OK: 組み込み完了")
else:
    print("NG: 挿入箇所が見つかりませんでした")
    # 末尾100文字確認
    print(repr(c[c.find("https://secure.freee") : c.find("https://secure.freee") + 200]))
