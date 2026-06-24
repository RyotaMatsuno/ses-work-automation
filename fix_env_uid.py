path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 旧IDを新IDに置換
old = "MATSUNO_LINE_USER_ID=Uac1d23408573586affa37577c4e2b2ab"
new = "MATSUNO_LINE_USER_ID=Ue3508b43b84991f5a68281da5bf4cf39"

if old in content:
    content = content.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("UPDATED OK")
else:
    # 現在の値を確認
    for line in content.splitlines():
        if "MATSUNO_LINE_USER_ID" in line:
            print("current:", line)
