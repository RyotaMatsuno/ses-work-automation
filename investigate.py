import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import requests
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = config.get("NOTION_TOKEN") or config.get("NOTION_API_KEY")
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}
ENG_DB = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"

# 全エンジニアの所属情報を取得
payload = {"page_size": 100}
pages = []
while True:
    r = requests.post(f"https://api.notion.com/v1/databases/{ENG_DB}/query", headers=headers, json=payload, timeout=15)
    d = r.json()
    pages.extend(d.get("results", []))
    if not d.get("has_more"):
        break
    payload["start_cursor"] = d["next_cursor"]


def gtext(p, key):
    prop = p.get("properties", {}).get(key, {})
    pt = prop.get("type")
    if pt == "title":
        return "".join(t.get("plain_text", "") for t in prop.get("title", []))
    if pt == "rich_text":
        return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))
    if pt == "email":
        return prop.get("email", "") or ""
    if pt == "select":
        return (prop.get("select") or {}).get("name", "")
    return ""


print("=" * 70)
print(f"エンジニアDB調査 (全{len(pages)}件)")
print("=" * 70)

# 問題のあるレコードを分類
issues = {"英語所属": [], "所属空欄": [], "所属メール空欄": [], "OK": []}

for p in pages:
    name = gtext(p, "名前")
    affil = gtext(p, "所属会社")
    affil_n = gtext(p, "所属会社名")
    cont = gtext(p, "所属担当者名")
    mail = gtext(p, "所属メール")
    ini = gtext(p, "イニシャル")
    sta = gtext(p, "最寄り駅")
    skill = [o["name"] for o in p.get("properties", {}).get("スキル", {}).get("multi_select", [])]
    memo = gtext(p, "備考（LINEメモ）")

    # 英語データの検出（ASCII比率が高い）
    is_english_affil = affil and all(ord(c) < 128 or c == " " for c in affil)

    row = {"name": name, "ini": ini, "sta": sta, "affil": affil, "cont": cont, "mail": mail, "memo": memo[:60]}

    if is_english_affil:
        issues["英語所属"].append(row)
    elif not affil and not affil_n:
        issues["所属空欄"].append(row)
    elif not mail and not cont:
        issues["所属メール空欄"].append(row)
    else:
        issues["OK"].append(row)

for category, rows in issues.items():
    if not rows:
        continue
    print(f"\n【{category}】 {len(rows)}件")
    for row in rows:
        print(f"  {row['ini'] or '??'} {row['name'][:12]}")
        print(f"    所属=[{row['affil'][:30]}] 担当=[{row['cont'][:20]}] メール=[{row['mail'][:30]}]")
        if row["memo"]:
            print(f"    備考: {row['memo'][:60]}")

print()
print("=" * 70)
print("根本原因分析")
print("=" * 70)
print()
print("【最重要問題】所属情報の欠落/英語化")
print()
print("原因A: LINE登録時のclassify_message が英語JSONで返す")
print("  webhook_server.pyのclassify_messageシステムプロンプトは英語")
print("  → affiliation, note 等のフィールドが英語で保存される")
print('  → "所属会社" = "Staffing company employee" (「弊社正社員」の英訳)')
print()
print("原因B: 元のLINEメッセージに所属会社名が書かれていない")
print('  "うちの社員の林が..." → 会社名が省略されている')
print('  → classify_messageが抽出しても空か "unknown"')
print()
print("原因C: 所属担当者名・所属メールが抽出されていない")
print("  LINE送信者の名前・メールは LINE APIから取得できない")
print("  → 送信者情報はLINEのuser_idのみで、名前/メールは取れない")
print()
print("【対応方針】")
print('  コード修正: 英語/空の所属は "所属: 確認要" として表示')
print("  手動対応: H.Sのレコードに所属会社・担当者・メールを手入力")
print("  将来対応: スキルシートPDF送付時に所属情報を自動抽出")
