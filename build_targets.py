import csv
import os

# スプレッドシートから抽出した会社データ
# 電話番号列にメアドが入っている会社 + 元請けリストのURL付き会社を整理

# メアドが明示的に存在する会社（本文から抽出）
mail_entries = [
    # 会社名, メアド, 種別
    ("有限会社ケープコム", "info@capecom.co.jp", "SES"),
    ("株式会社ビッグタウンズ", "info@bigtowns.co.jp", "SES"),
    ("株式会社BASIS", "info@e-basis.co.jp", "SES"),
    ("アイムファクトリー株式会社", "tasaki@aim-factory.com", "SES"),
    ("アラスジャパン株式会社", "community-japan@aras.com", "SES"),
    ("アキュラスター株式会社", "tatsuki.kaibara@aqurastar.co.jp", "SES"),
    ("アイピーティシステムズ有限会社", "info@ipt-systems.com", "SES"),
    ("TJサーチ＆カンパニー株式会社", "info@tjsearch.co.jp", "SES"),
    ("omeroid株式会社", "inquiry@omeroid.com", "SES"),
    ("RON株式会社", "consulting@ron.style", "SES"),
    ("En-Technology株式会社", "info@en-technology.co.jp", "SES"),
    ("DXHR株式会社", "aoyagi@dxhr.inc", "SES"),
    ("dongoon株式会社", "pilot_window@dongoon.jp", "SES"),
    ("CFL株式会社", "miki.ando@cfl-re.co.jp", "SES"),
    ("BLKS株式会社", "oyama@blks.tokyo", "SES"),
    ("INCREDS株式会社", "info@increds.co.jp", "SES"),
    ("G-new's株式会社", "", "SES"),  # メール送信可能
    ("GENEST株式会社", "", "SES"),
    ("Filanza株式会社", "", "SES"),
    # 元請けリスト（問い合わせフォームあり）
    ("CTCテクノロジー株式会社", "", "元請け"),
    ("株式会社エイ・エス・ピー", "", "元請け"),
    ("株式会社セゾンテクノロジー", "", "元請け"),
    ("日本ビジネスシステムズ株式会社", "", "元請け"),
    ("日鉄日立システムソリューションズ株式会社", "", "元請け"),
    ("株式会社ゼストエンタープライズ", "", "元請け"),
]

# メアドありのみ抽出
valid = [(name, mail, typ) for name, mail, typ in mail_entries if mail]

base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
csv_path = os.path.join(base, "outreach_system", "targets.csv")

# 既存CSVを読んで会社名の重複チェック
existing = set()
if os.path.exists(csv_path):
    with open(csv_path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            existing.add(row.get("company", "").strip())

# 追記
new_rows = []
for name, mail, typ in valid:
    if name not in existing:
        new_rows.append({"company": name, "contact_name": "", "email": mail, "type": typ, "memo": ""})

# 新規CSVとして書き出し（既存のサンプルを置き換え）
all_rows = [{"company": n, "contact_name": "", "email": m, "type": t, "memo": ""} for n, m, t in valid]

with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["company", "contact_name", "email", "type", "memo"])
    writer.writeheader()
    writer.writerows(all_rows)

print(f"targets.csv: {len(all_rows)}社（メアドあり）を書き込み完了")
for r in all_rows:
    print(f"  {r['type']}: {r['company']} -> {r['email']}")
