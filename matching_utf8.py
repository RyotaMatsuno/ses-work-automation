
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import os, requests
from dotenv import dotenv_values

env_path = os.path.join(os.path.dirname(__file__), 'config', '.env')
config = dotenv_values(env_path)
for k, v in config.items():
    if k not in os.environ:
        os.environ[k] = v

API_KEY        = os.environ.get('NOTION_API_KEY', '')
ENGINEER_DB_ID = os.environ.get('NOTION_ENGINEER_DB_ID', '')
PROJECT_DB_ID  = os.environ.get('NOTION_PROJECT_DB_ID', '343450ff-37c0-81e4-934e-f25f90284a3c')

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def query_db(db_id, filter_obj=None):
    results = []
    payload = {"page_size": 100}
    if filter_obj:
        payload["filter"] = filter_obj
    while True:
        r = requests.post(
            f"https://api.notion.com/v1/databases/{db_id}/query",
            headers=HEADERS, json=payload
        )
        data = r.json()
        results.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data["next_cursor"]
    return results

def get_ms(props, key):
    return [o["name"] for o in props.get(key, {}).get("multi_select", [])]

def get_title(props, key):
    items = props.get(key, {}).get("title", [])
    return items[0]["plain_text"] if items else "（名前なし）"

def get_number(props, key):
    return props.get(key, {}).get("number")

def get_date(props, key):
    d = props.get(key, {}).get("date")
    return d["start"] if d else None

def get_rt(props, key):
    rt = props.get(key, {}).get("rich_text", [])
    return rt[0]["plain_text"] if rt else ""

def mark(b): return "○" if b else "✕"

def main():
    print("=" * 60)
    print("案件 × エンジニア マッチング結果")
    print("=" * 60)

    projects = query_db(PROJECT_DB_ID, {
        "property": "ステータス", "select": {"equals": "募集中"}
    })
    engineers = query_db(ENGINEER_DB_ID, {
        "property": "稼働状況", "select": {"equals": "稼働可能"}
    })
    print(f"募集中案件: {len(projects)}件 / 稼働可能エンジニア: {len(engineers)}名\n")

    if not engineers:
        print("稼働可能エンジニアなし")
        return

    # エンジニア一覧も出力
    print("【稼働可能エンジニア一覧】")
    for eng in engineers:
        ep = eng["properties"]
        name   = get_title(ep, "名前")
        skills = get_ms(ep, "スキル")
        price  = get_number(ep, "単価（万円）")
        avail  = get_date(ep, "稼働可能日")
        print(f"  {name} | {price}万 | {avail or '即日'} | {', '.join(skills)}")
    print()

    # マッチング
    matched_any = False
    for proj in projects:
        pp = proj["properties"]
        pname    = get_title(pp, "案件名")
        required = set(get_ms(pp, "必要スキル"))
        optional = set(get_ms(pp, "尚可スキル"))
        pprice   = get_number(pp, "単価（万円）")
        client   = get_rt(pp, "クライアント")

        candidates = []
        for eng in engineers:
            ep = eng["properties"]
            ename  = get_title(ep, "名前")
            eskills = set(get_ms(ep, "スキル"))
            eprice  = get_number(ep, "単価（万円）")
            eavail  = get_date(ep, "稼働可能日")

            if required and not required.issubset(eskills):
                continue
            if pprice and eprice and eprice > pprice + 10:
                continue

            opt_match = len(optional & eskills)
            opt_total = len(optional)
            opt_rate  = opt_match / opt_total if opt_total > 0 else 1.0

            # 粗利計算（エンジニア単価がある場合）
            gross = pprice - eprice if pprice and eprice else None

            candidates.append({
                "name": ename, "skills": eskills, "price": eprice,
                "avail": eavail, "required": required, "optional": optional,
                "opt_rate": opt_rate, "opt_match": opt_match, "opt_total": opt_total,
                "gross": gross
            })

        if not candidates:
            continue

        matched_any = True
        print(f"【案件】{pname}（{client}）| 単価{pprice}万 | 必須:{','.join(sorted(required)) or 'なし'}")
        print(f"  → 候補 {len(candidates)}名")

        # 粗利降順でソート
        candidates.sort(key=lambda x: (x["gross"] or 0), reverse=True)

        for c in candidates[:5]:  # 上位5名まで表示
            req_str = "  ".join(f"{s}:{mark(s in c['skills'])}" for s in sorted(c["required"])) if c["required"] else "なし"
            opt_str = f"{c['opt_match']}/{c['opt_total']}項目" if c["opt_total"] > 0 else "-"
            gross_str = f"粗利{c['gross']}万" if c["gross"] else "粗利不明"
            print(f"    ▶ {c['name']} | {c['price']}万 | {gross_str} | 必須:{req_str} | 尚可:{opt_str} | {c['avail'] or '即日'}")
        print()

    if not matched_any:
        print("マッチする組み合わせなし（必須スキル不一致または単価乖離）")

    print("=" * 60)
    print("完了")

if __name__ == "__main__":
    main()
