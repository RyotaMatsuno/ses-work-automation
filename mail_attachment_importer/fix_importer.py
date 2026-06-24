p = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_attachment_importer\importer.py"
with open(p, "r", encoding="utf-8") as f:
    c = f.read()

old = "emails = fetch_new_emails(days_back=30)"
new = "emails = fetch_new_emails(days_back=1)  # 毎日実行想定: 1日分のみ処理"

if old in c:
    c = c.replace(old, new)
    with open(p, "w", encoding="utf-8") as f:
        f.write(c)
    print("importer.py: days_back=30 -> 1 に変更完了")
else:
    print("Pattern not found")
