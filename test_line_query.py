import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ローカルでline_queryの「HS 北小金」を直接テスト
import os

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook")
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")

# 環境変数を設定
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
for k, v in config.items():
    os.environ.setdefault(k, v)

print("=== line_queryローカルテスト ===")
print()

# line_queryをインポート
from line_query import (
    _match_initial,
    _match_station,
    _normalize_initial,
    classify_query,
    engineer_query,
    handle_line_query,
)

print('--- テスト1: classify_query("HS 北小金") ---')
qtype, params = classify_query("HS 北小金")
print(f"type={qtype}, params={params}")
print()

print('--- テスト2: classify_query("H.S 北小金") ---')
qtype, params = classify_query("H.S 北小金")
print(f"type={qtype}, params={params}")
print()

print('--- テスト3: _normalize_initial("H.S") ---')
result = _normalize_initial("H.S")
print(f'_normalize_initial("H.S") = "{result}"')
print()

# Notionからエンジニアを取得してテスト
import requests

ENGINEER_DB = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"
token = config.get("NOTION_TOKEN") or config.get("NOTION_API_KEY")
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}

r = requests.post(f"https://api.notion.com/v1/databases/{ENGINEER_DB}/query", headers=headers, json={"page_size": 100})
pages = r.json().get("results", [])

print("--- テスト4: H.Sレコードの現在状態 ---")
for p in pages:
    props = p.get("properties", {})
    name_items = props.get("名前", {}).get("title", [])
    name = "".join(t.get("plain_text", "") for t in name_items)
    if name == "H.S":
        ini_items = props.get("イニシャル", {}).get("rich_text", [])
        ini = "".join(t.get("plain_text", "") for t in ini_items)
        sta_items = props.get("最寄り駅", {}).get("rich_text", [])
        sta = "".join(t.get("plain_text", "") for t in sta_items)
        print(f"  名前: {name}")
        print(f"  イニシャル: [{ini}]")
        print(f"  最寄り駅: [{sta}]")

        # _match_initial テスト
        fake_engineer = {"properties": p["properties"]}
        # 実際のengineersリストの要素形式で
        result_ini = _match_initial(p, "HS")
        result_sta = _match_station(p, "北小金")
        print(f"  _match_initial(HS): {result_ini}")
        print(f"  _match_station(北小金): {result_sta}")
        break
print()

print('--- テスト5: engineer_query("HS", "北小金") 実行 ---')
result = engineer_query("HS", "北小金")
print(result[:500] if result else "(空)")
print()

print('--- テスト6: handle_line_query("HS 北小金") ---')
result = handle_line_query("HS 北小金")
print(result[:500] if result else "None (スルー)")
print()

print('--- テスト7: handle_line_query("H.S 北小金") ---')
result = handle_line_query("H.S 北小金")
print(result[:500] if result else "None (スルー)")
