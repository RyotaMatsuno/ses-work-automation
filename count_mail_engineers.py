import requests
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
NOTION_KEY = config["NOTION_API_KEY"]
ENGINEER_DB = config["NOTION_ENGINEER_DB_ID"]

headers = {"Authorization": f"Bearer {NOTION_KEY}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}

# 入力元="共通メール" or "松野メール" or "岡本メール" のエンジニアを集計
results = []
cursor = None
while True:
    payload = {"page_size": 100}
    if cursor:
        payload["start_cursor"] = cursor
    r = requests.post(
        f"https://api.notion.com/v1/databases/{ENGINEER_DB}/query", headers=headers, json=payload, timeout=30
    )
    data = r.json()
    for page in data.get("results", []):
        props = page["properties"]
        # 入力元プロパティを確認
        input_source = props.get("入力元", {}).get("select", {})
        input_source_name = input_source.get("name", "") if input_source else ""
        # 備考にメール登録フラグがあるか
        note_items = props.get("備考（LINEメモ）", {}).get("rich_text", [])
        note = note_items[0]["plain_text"] if note_items else ""
        is_mail = "メールから自動登録" in note
        name_items = props.get("名前", {}).get("title", [])
        name = name_items[0]["plain_text"] if name_items else "?"
        results.append({"id": page["id"], "name": name, "input_source": input_source_name, "is_mail": is_mail})
    if not data.get("has_more"):
        break
    cursor = data["next_cursor"]

mail_engineers = [r for r in results if r["is_mail"]]
line_engineers = [r for r in results if not r["is_mail"]]

print(f"全エンジニア: {len(results)}名")
print(f"メール経由（削除対象）: {len(mail_engineers)}名")
print(f"LINE/その他: {len(line_engineers)}名")
print()
print("--- 削除対象サンプル（最初の10名）---")
for e in mail_engineers[:10]:
    print(f"  {e['name']} | 入力元: {e['input_source']}")
