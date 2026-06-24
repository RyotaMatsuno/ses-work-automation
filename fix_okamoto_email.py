import sys

sys.stdout.reconfigure(encoding="utf-8")

IMP = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_attachment_importer"
mf_path = IMP + r"\mail_fetcher.py"

with open(mf_path, encoding="utf-8") as f:
    mf = f.read()

# _get_account_config内のokamotoパスワード取得ロジックを確認
# 現状: OKAMOTO_PASSWORDかOKAMOTO_MAIL_PASSWORDを参照しているか？
# 追加したキーはOKAMOTO_PASSWORD なのでprefixパターンで拾えるはず

# email設定も確認（OKAMOTO_EMAILが未設定だとデフォルトが空になる）
old_email_line = (
    '"email": os.environ.get(f"{prefix}_EMAIL", "sessales@terra-ltd.co.jp" if account == "sessales" else ""),'
)
new_email_line = (
    '"email": os.environ.get(f"{prefix}_EMAIL", '
    '"sessales@terra-ltd.co.jp" if account == "sessales" else '
    '"r-matsuno@terra-ltd.co.jp" if account == "matsuno" else '
    '"r-okamoto@terra-ltd.co.jp" if account == "okamoto" else ""),'
)

if old_email_line in mf:
    mf = mf.replace(old_email_line, new_email_line, 1)
    with open(mf_path, "w", encoding="utf-8") as f:
        f.write(mf)
    print("メールアドレスデフォルト値修正OK")
elif "r-okamoto@terra-ltd.co.jp" in mf:
    print("okamotoデフォルトアドレス: 既に設定済み")
else:
    print("対象行が見つかりません（現状確認）")
    for line in mf.split("\n"):
        if "_EMAIL" in line and "environ" in line:
            print(" ", repr(line))
