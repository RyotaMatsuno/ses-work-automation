import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import requests
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = config.get("NOTION_TOKEN") or config.get("NOTION_API_KEY")
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}

ENG_DB = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"
PROJ_DB = "343450ff-37c0-81e4-934e-f25f90284a3c"

# 定数値
PROP_INI = bytes.fromhex("e382a4e3838be382b7e383a3e383ab").decode()
PROP_NAME = bytes.fromhex("e5908de5898d").decode()
PROP_STA = bytes.fromhex("e69c80e5af84e3828ae9a785").decode()
PROP_SKILL = bytes.fromhex("e382b9e382ade383ab").decode()
PROP_RATE = bytes.fromhex("e58d98e4bea1efbc88e4b887e58686efbc89").decode()
PROP_STATUS = bytes.fromhex("e382b9e38386e383bce382bfe382b9").decode()
PROP_REQSK = bytes.fromhex("e5bf85e8a681e382b9e382ade383ab").decode()
PROP_OPTSK = bytes.fromhex("e5b09ae58fafe382b9e382ade383ab").decode()  # 修正後
PROP_ASSIGNEE = bytes.fromhex("e68b85e5bd93e88085").decode()
PROP_PJNAME = bytes.fromhex("e6a188e4bbb6e5908d").decode()
PROP_REMOTE = bytes.fromhex("e383aae383a2e383bce38388").decode()
PROP_LOCATION = bytes.fromhex("e58ba4e58b99e59cb0").decode()
PROP_PERIOD = bytes.fromhex("e69c9fe99693").decode()
PROP_WORKST = bytes.fromhex("e7a8bce5838de78ab6e6b381").decode()
PROP_WORKON = bytes.fromhex("e7a8bce5838de58fafe883bde697a5").decode()

print("=== エンジニアDB プロパティ名 実照合 ===")
r = requests.post(
    f"https://api.notion.com/v1/databases/{ENG_DB}/query", headers=headers, json={"page_size": 1}, timeout=15
)
eng_props = set(r.json()["results"][0]["properties"].keys()) if r.json().get("results") else set()
for prop in [PROP_INI, PROP_NAME, PROP_STA, PROP_SKILL, PROP_RATE, PROP_WORKST, PROP_WORKON, PROP_ASSIGNEE]:
    found = prop in eng_props
    print(f"  {'✅' if found else '❌'} '{prop}'")

print()
print("=== 案件DB プロパティ名 実照合 ===")
r2 = requests.post(
    f"https://api.notion.com/v1/databases/{PROJ_DB}/query", headers=headers, json={"page_size": 1}, timeout=15
)
proj_props = set(r2.json()["results"][0]["properties"].keys()) if r2.json().get("results") else set()
for prop in [
    PROP_PJNAME,
    PROP_STATUS,
    PROP_REQSK,
    PROP_OPTSK,
    PROP_RATE,
    PROP_ASSIGNEE,
    PROP_REMOTE,
    PROP_LOCATION,
    PROP_PERIOD,
]:
    found = prop in proj_props
    print(f"  {'✅' if found else '❌'} '{prop}'")

# 尚可スキルが案件DBに実在するか
print()
print(
    f"PROP_OPTSK ({PROP_OPTSK}) 案件DBに存在: {'✅' if PROP_OPTSK in proj_props else '❌（このカラムがDB上に存在しない）'}"
)
print()
# 全プロパティ表示
print("--- 案件DBの全プロパティ名 ---")
for p in sorted(proj_props):
    print(f"  [{p}]")
