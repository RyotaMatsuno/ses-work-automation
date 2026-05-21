
# sheets_reader.pyの岡本新営業分岐を追加
path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\sheets_reader.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

old = "        if tantou == \"小坂折半\":\n            seikyu, rule = int(profit * 0.48), \"小坂折半→粗利×48%\"\n        elif tantou in (\"岡本折半\",\"岡本\"):\n            seikyu, rule = int(profit * 0.68), f\"{tantou}→粗利×68%\"\n        else:\n            seikyu, rule = int(profit * 0.68), \"通常→粗利×68%\""

new = "        if tantou == \"小坂折半\":\n            seikyu, rule = int(profit * 0.48), \"小坂折半→粗利×48%\"\n        elif tantou == \"岡本新営業\":\n            seikyu, rule = int(profit * 0.68), \"岡本新営業→粗利×68%（払出20%）\"\n        elif tantou in (\"岡本折半\",\"岡本\"):\n            seikyu, rule = int(profit * 0.68), f\"{tantou}→粗利×68%\"\n        else:\n            seikyu, rule = int(profit * 0.68), \"通常→粗利×68%\""

content = content.replace(old, new)
with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("sheets_reader.py 更新完了")
