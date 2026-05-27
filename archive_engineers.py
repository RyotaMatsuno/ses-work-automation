import sys, io, requests
from dotenv import dotenv_values

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

cfg = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
NOTION_KEY = cfg["NOTION_API_KEY"]

headers = {
    "Authorization": f"Bearer {NOTION_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

# ②田中太郎 + ③稼働日古い12件 → archived=True（Notionのゴミ箱送り）
target_ids = [
    # ②田中太郎
    "360450ff-37c0-8108-a959-f2c94c09a611",
    # ③稼働日古い12件
    "35d450ff-37c0-817d-9621-c043ece328d3",  # LHS 2024-07-01
    "35d450ff-37c0-8123-b8bb-c139bad439fa",  # 王YX 2025-06-01
    "35d450ff-37c0-8104-9441-d0e1e0eafd87",  # Y.T 2025-05-08
    "35d450ff-37c0-8130-89a9-fdd9aa18626a",  # Y.K 2025-07-01
    "35d450ff-37c0-8196-8a70-c9155f10a823",  # TK 2025-05-01
    "35d450ff-37c0-8157-becf-d10f668d1740",  # I.Y 2025-04-01
    "35d450ff-37c0-814b-9bbe-fc91a88413f6",  # K.D 2025-06-01
    "35d450ff-37c0-81d0-8f84-ff98e15eafc6",  # Y.T 2025-05-01
    "35d450ff-37c0-8103-b592-cc2327c6fac2",  # E.S 2025-04-01
    "35b450ff-37c0-812f-bfa0-f5a009e24771",  # M.S 2025-06-01
    "35b450ff-37c0-81bd-a221-e448d380162e",  # N.Y 2025-05-01
    "35b450ff-37c0-81fd-a486-f18537cc0363",  # T.T 2025-05-01
]

names = {
    "360450ff-37c0-8108-a959-f2c94c09a611": "田中太郎（テストデータ）",
    "35d450ff-37c0-817d-9621-c043ece328d3": "LHS(40歳/男性) 2024-07-01",
    "35d450ff-37c0-8123-b8bb-c139bad439fa": "王YX 2025-06-01",
    "35d450ff-37c0-8104-9441-d0e1e0eafd87": "Y.T 2025-05-08",
    "35d450ff-37c0-8130-89a9-fdd9aa18626a": "Y.K 2025-07-01",
    "35d450ff-37c0-8196-8a70-c9155f10a823": "TK 2025-05-01",
    "35d450ff-37c0-8157-becf-d10f668d1740": "I.Y 2025-04-01",
    "35d450ff-37c0-814b-9bbe-fc91a88413f6": "K.D 2025-06-01",
    "35d450ff-37c0-81d0-8f84-ff98e15eafc6": "Y.T 2025-05-01",
    "35d450ff-37c0-8103-b592-cc2327c6fac2": "E.S 2025-04-01",
    "35b450ff-37c0-812f-bfa0-f5a009e24771": "M.S 2025-06-01",
    "35b450ff-37c0-81bd-a221-e448d380162e": "N.Y 2025-05-01",
    "35b450ff-37c0-81fd-a486-f18537cc0363": "T.T 2025-05-01",
}

success = []
fail = []

for page_id in target_ids:
    r = requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=headers,
        json={"archived": True}
    )
    if r.status_code == 200:
        success.append(names[page_id])
        print(f"✅ アーカイブ完了: {names[page_id]}")
    else:
        fail.append(names[page_id])
        print(f"❌ 失敗: {names[page_id]} / {r.status_code} {r.text[:100]}")

print()
print(f"完了: {len(success)}件 / 失敗: {len(fail)}件")
