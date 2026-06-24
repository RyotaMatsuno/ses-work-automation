import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook")
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
import requests
from dotenv import dotenv_values

ENV_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env"
config = dotenv_values(ENV_PATH)
token = config.get("NOTION_TOKEN") or config.get("NOTION_API_KEY")
ENGINEER_DB = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"
PROJECT_DB = "343450ff-37c0-81e4-934e-f25f90284a3c"

headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}

# === STEP1: エンジニアDBの実際のプロパティキー名を確認 ===
print("=== STEP1: エンジニアDB プロパティキー名一覧 ===")
r = requests.post(f"https://api.notion.com/v1/databases/{ENGINEER_DB}/query", headers=headers, json={"page_size": 3})
data = r.json()
if data.get("results"):
    props = data["results"][0].get("properties", {})
    for k in sorted(props.keys()):
        print(f"  キー: [{k}] ({len(k)}chars) hex={k.encode('utf-8').hex()[:20]}")

print()

# === STEP2: HS（林 北小金）に相当するエンジニアを探す ===
print('=== STEP2: "HS" or "北小金" を含むエンジニア検索 ===')
all_pages = []
payload = {"page_size": 100}
while True:
    r = requests.post(f"https://api.notion.com/v1/databases/{ENGINEER_DB}/query", headers=headers, json=payload)
    d = r.json()
    all_pages.extend(d.get("results", []))
    if not d.get("has_more"):
        break
    payload["start_cursor"] = d["next_cursor"]

print(f"全エンジニア数: {len(all_pages)}件")


# イニシャル・名前・最寄り駅の全組み合わせを確認
def get_text(page, key):
    prop = page.get("properties", {}).get(key, {})
    ptype = prop.get("type")
    if ptype == "title":
        return "".join(t.get("plain_text", "") for t in prop.get("title", []))
    elif ptype == "rich_text":
        return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))
    return ""


# 実際のキー名で取得
prop_keys = list(data["results"][0].get("properties", {}).keys()) if data.get("results") else []
ini_keys = [k for k in prop_keys if "ニシャル" in k or "initial" in k.lower()]
name_keys = [k for k in prop_keys if "名前" in k or "name" in k.lower()]
sta_keys = [k for k in prop_keys if "最寄" in k or "駅" in k or "station" in k.lower()]
memo_keys = [k for k in prop_keys if "備考" in k or "memo" in k.lower()]

print(f"イニシャル候補キー: {ini_keys}")
print(f"名前候補キー: {name_keys}")
print(f"最寄り駅候補キー: {sta_keys}")
print(f"備考候補キー: {memo_keys}")

print()
print("=== HS・林・北小金 に関係するエンジニアレコード ===")
for page in all_pages:
    props = page.get("properties", {})
    # 全テキスト値を収集
    texts = {}
    for k, v in props.items():
        ptype = v.get("type")
        if ptype == "title":
            t = "".join(x.get("plain_text", "") for x in v.get("title", []))
        elif ptype == "rich_text":
            t = "".join(x.get("plain_text", "") for x in v.get("rich_text", []))
        elif ptype == "select":
            t = v.get("select", {}).get("name", "") if v.get("select") else ""
        elif ptype == "multi_select":
            t = ",".join(x.get("name", "") for x in v.get("multi_select", []))
        elif ptype == "number":
            t = str(v.get("number", ""))
        else:
            t = ""
        texts[k] = t

    all_text = " ".join(texts.values())
    if any(kw in all_text for kw in ["HS", "H.S", "林", "北小金", "HB", "Hayashi"]):
        print("\n--- FOUND ---")
        for k, v in texts.items():
            if v:
                print(f"  {k}: {v}")
        # 最終更新
        print(f"  last_edited: {page.get('last_edited_time', '?')}")
