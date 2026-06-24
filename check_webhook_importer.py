# attachment_importerの本番フロー確認
# LINEからテキストが来た際の想定フローをシミュレート

import os

base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"

# webhook_server.py がimporterをどう呼んでいるか確認
wh = os.path.join(base, "line_webhook", "webhook_server.py")
with open(wh, encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if any(k in line for k in ["attachment", "importer", "import_", "スキルシート", "attach"]):
        print(f"{i + 1}: {line}", end="")
