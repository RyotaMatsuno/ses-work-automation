"""
案件 × エンジニア マッチングスクリプト
- 必須スキルを全て持つエンジニアのみ候補に絞る
- 必須スキル・尚可スキルそれぞれ ◯/✕ で表示
"""

import os

import requests
from dotenv import dotenv_values

env_path = os.path.join(os.path.dirname(__file__), "config", ".env")
config = dotenv_values(env_path)
for k, v in config.items():
    if k not in os.environ:
        os.environ[k] = v

API_KEY = os.environ.get("NOTION_API_KEY", "")
ENGINEER_DB_ID = os.environ.get("NOTION_ENGINEER_DB_ID", "")
PROJECT_DB_ID = os.environ.get("NOTION_PROJECT_DB_ID", "343450ff-37c0-81e4-934e-f25f90284a3c")

HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}


def query_db(db_id, filter_obj=None):
    results = []
    payload = {"page_size": 100}
    if filter_obj:
        payload["filter"] = filter_obj
    while True:
        r = requests.post(f"https://api.notion.com/v1/databases/{db_id}/query", headers=HEADERS, json=payload)
        data = r.json()
        results.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data["next_cursor"]
    return results


def get_multiselect(props, key):
    return [o["name"] for o in props.get(key, {}).get("multi_select", [])]


def get_title(props, key):
    items = props.get(key, {}).get("title", [])
    return items[0]["plain_text"] if items else "（名前なし）"


def get_number(props, key):
    return props.get(key, {}).get("number")


def get_date(props, key):
    d = props.get(key, {}).get("date")
    return d["start"] if d else None


def get_select(props, key):
    s = props.get(key, {}).get("select")
    return s["name"] if s else None


def mark(has: bool) -> str:
    return "◯" if has else "✕"


def main():
    print("=" * 65)
    print("案件 × エンジニア マッチング")
    print("=" * 65)

    # 案件DBから募集中の案件を取得
    projects = query_db(PROJECT_DB_ID, {"property": "ステータス", "select": {"equals": "募集中"}})
    print(f"案件: {len(projects)}件（募集中）")

    # エンジニアDBから稼働可能なエンジニアを取得
    engineers = query_db(ENGINEER_DB_ID, {"property": "稼働状況", "select": {"equals": "稼働可能"}})
    print(f"エンジニア: {len(engineers)}名（稼働可能）\n")

    if not projects:
        print("募集中の案件がありません。")
        return
    if not engineers:
        print("稼働可能なエンジニアがいません。")
        return

    for proj in projects:
        pp = proj["properties"]
        proj_name = get_title(pp, "案件名")
        required = set(get_multiselect(pp, "必要スキル"))
        optional = set(get_multiselect(pp, "尚可スキル"))
        proj_price = get_number(pp, "単価（万円）")
        proj_start = get_date(pp, "開始日")
        client = pp.get("クライアント", {}).get("rich_text", [])
        client_name = client[0]["plain_text"] if client else "不明"

        print("=" * 65)
        print(f"【案件】{proj_name}")
        print(f"  クライアント : {client_name}")
        print(f"  必須スキル   : {', '.join(sorted(required)) or 'なし'}")
        print(f"  尚可スキル   : {', '.join(sorted(optional)) or 'なし'}")
        print(f"  単価         : {proj_price}万円" if proj_price else "  単価         : 未設定")
        print(f"  開始日       : {proj_start or '未設定'}")
        print()

        candidates = []
        for eng in engineers:
            ep = eng["properties"]
            eng_name = get_title(ep, "名前")
            eng_skills = set(get_multiselect(ep, "スキル"))
            eng_price = get_number(ep, "単価（万円）")
            eng_avail = get_date(ep, "稼働可能日")

            # 必須スキルを全て持っているか（フィルタ条件）
            if required and not required.issubset(eng_skills):
                continue

            # 単価チェック（案件単価がある場合、エンジニア希望が超過していたらスキップ）
            if proj_price and eng_price and eng_price > proj_price + 10:
                continue

            candidates.append(
                {
                    "name": eng_name,
                    "skills": eng_skills,
                    "price": eng_price,
                    "avail": eng_avail,
                    "required": required,
                    "optional": optional,
                }
            )

        if not candidates:
            print("  → マッチするエンジニアなし\n")
            continue

        print(f"  候補エンジニア: {len(candidates)}名")
        print("-" * 65)

        for c in candidates:
            print(f"\n  >> {c['name']}")
            print(f"    単価: {c['price']}万円 / 稼働可能日: {c['avail'] or '未設定'}")

            # 必須スキル ◯/✕
            if c["required"]:
                req_str = "  ".join(f"{s}:{mark(s in c['skills'])}" for s in sorted(c["required"]))
                print(f"    必須スキル: {req_str}")

            # 尚可スキル ◯/✕
            if c["optional"]:
                opt_str = "  ".join(f"{s}:{mark(s in c['skills'])}" for s in sorted(c["optional"]))
                print(f"    尚可スキル: {opt_str}")

        print()

    print("=" * 65)
    print("マッチング完了")


if __name__ == "__main__":
    main()
