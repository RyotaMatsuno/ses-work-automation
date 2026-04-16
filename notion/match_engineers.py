"""
エンジニア × 案件 自動マッチングスクリプト

NotionのエンジニアDBと案件DBを照合して
スキル・単価・稼働日が条件に合う組み合わせを出力する

実行:
  python match_engineers.py
"""

import os
import requests
from dotenv import dotenv_values
from datetime import datetime

# .envロード
env_path = os.path.join(os.path.dirname(__file__), '..', 'config', '.env')
if os.path.exists(env_path):
    config = dotenv_values(env_path)
    for key, value in config.items():
        if key not in os.environ:
            os.environ[key] = value

NOTION_API_KEY        = os.environ['NOTION_API_KEY']
NOTION_ENGINEER_DB_ID = os.environ['NOTION_ENGINEER_DB_ID']
NOTION_PROJECT_DB_ID  = os.environ['NOTION_PROJECT_DB_ID']

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}


def get_all_pages(database_id: str) -> list:
    """NotionDBの全ページを取得"""
    results = []
    payload = {"page_size": 100}
    while True:
        res = requests.post(
            f"https://api.notion.com/v1/databases/{database_id}/query",
            headers=HEADERS,
            json=payload
        )
        data = res.json()
        results.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data["next_cursor"]
    return results


def extract_engineer(page: dict) -> dict:
    """エンジニアページからデータ抽出"""
    props = page["properties"]
    def text(p): return p["title"][0]["text"]["content"] if p.get("title") else ""
    def multi(p): return [o["name"] for o in p.get("multi_select", [])]
    def num(p): return p.get("number")
    def sel(p): return p["select"]["name"] if p.get("select") else ""
    def date(p): return p["date"]["start"] if p.get("date") else None

    return {
        "id": page["id"],
        "url": page["url"],
        "name": text(props.get("名前", {})),
        "skills": multi(props.get("スキル", {})),
        "price": num(props.get("単価（万円）", {})),
        "status": sel(props.get("稼働状況", {})),
        "available_date": date(props.get("稼働可能日", {})),
        "experience": num(props.get("経験年数", {})),
    }


def extract_project(page: dict) -> dict:
    """案件ページからデータ抽出"""
    props = page["properties"]
    def text(p): return p["title"][0]["text"]["content"] if p.get("title") else ""
    def multi(p): return [o["name"] for o in p.get("multi_select", [])]
    def num(p): return p.get("number")
    def sel(p): return p["select"]["name"] if p.get("select") else ""
    def date(p): return p["date"]["start"] if p.get("date") else None

    return {
        "id": page["id"],
        "url": page["url"],
        "name": text(props.get("案件名", {})),
        "required_skills": multi(props.get("必要スキル", {})),
        "budget": num(props.get("単価（万円）", {})),
        "status": sel(props.get("ステータス", {})),
        "start_date": date(props.get("開始日", {})),
    }


def calculate_score(engineer: dict, project: dict) -> tuple[int, list]:
    """マッチングスコア計算（0〜100点）"""
    score = 0
    reasons = []

    # スキルマッチ（最大50点）
    eng_skills = set(engineer["skills"])
    req_skills = set(project["required_skills"])
    if req_skills:
        matched = eng_skills & req_skills
        skill_score = int(len(matched) / len(req_skills) * 50)
        score += skill_score
        if matched:
            reasons.append(f"スキル一致: {', '.join(matched)} ({skill_score}pt)")
    else:
        score += 25
        reasons.append("スキル条件なし(+25pt)")

    # 稼働状況（20点）
    if engineer["status"] == "稼働可能":
        score += 20
        reasons.append("稼働可能(+20pt)")
    elif engineer["status"] == "調整中":
        score += 10
        reasons.append("調整中(+10pt)")

    # 単価マッチ（20点）
    eng_price = engineer["price"]
    proj_budget = project["budget"]
    if eng_price and proj_budget:
        diff = proj_budget - eng_price
        if diff >= 0:
            score += 20
            reasons.append(f"単価OK: {eng_price}万 <= {proj_budget}万(+20pt)")
        elif diff >= -5:
            score += 10
            reasons.append(f"単価ほぼOK: {eng_price}万 / 予算{proj_budget}万(+10pt)")
        else:
            reasons.append(f"単価超過: {eng_price}万 / 予算{proj_budget}万(0pt)")
    else:
        score += 10
        reasons.append("単価未設定(+10pt)")

    # 稼働可能日（10点）
    if engineer["available_date"] and project["start_date"]:
        if engineer["available_date"] <= project["start_date"]:
            score += 10
            reasons.append(f"稼働日OK(+10pt)")
        else:
            reasons.append(f"稼働日NG: {engineer['available_date']} > {project['start_date']}")
    else:
        score += 5
        reasons.append("稼働日未設定(+5pt)")

    return score, reasons


def run(min_score: int = 50):
    """マッチング実行"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] マッチング開始\n")

    print("エンジニアDB取得中...")
    eng_pages = get_all_pages(NOTION_ENGINEER_DB_ID)
    engineers = [extract_engineer(p) for p in eng_pages]
    # 稼働可能・調整中のみ対象
    active_engineers = [e for e in engineers if e["status"] in ["稼働可能", "調整中"]]
    print(f"  対象エンジニア: {len(active_engineers)}人（全{len(engineers)}人中）")

    print("案件DB取得中...")
    proj_pages = get_all_pages(NOTION_PROJECT_DB_ID)
    projects = [extract_project(p) for p in proj_pages]
    # 募集中のみ対象
    active_projects = [p for p in projects if p["status"] == "募集中"]
    print(f"  募集中案件: {len(active_projects)}件（全{len(projects)}件中）\n")

    if not active_engineers:
        print("稼働可能なエンジニアがいません")
        return
    if not active_projects:
        print("募集中の案件がありません")
        return

    # 全組み合わせでスコア計算
    matches = []
    for project in active_projects:
        for engineer in active_engineers:
            score, reasons = calculate_score(engineer, project)
            if score >= min_score:
                matches.append({
                    "score": score,
                    "engineer": engineer,
                    "project": project,
                    "reasons": reasons
                })

    # スコア降順でソート
    matches.sort(key=lambda x: x["score"], reverse=True)

    print(f"{'='*60}")
    print(f"マッチング結果（スコア{min_score}点以上）: {len(matches)}件")
    print(f"{'='*60}\n")

    for m in matches:
        eng = m["engineer"]
        proj = m["project"]
        print(f"[{m['score']}点] {eng['name']} × {proj['name']}")
        print(f"  エンジニア: スキル={eng['skills']} / 単価={eng['price']}万 / {eng['status']}")
        print(f"  案件: 必要スキル={proj['required_skills']} / 予算={proj['budget']}万")
        print(f"  理由: {' / '.join(m['reasons'])}")
        print(f"  エンジニア: {eng['url']}")
        print(f"  案件: {proj['url']}")
        print()

    if not matches:
        print("条件に合うマッチングが見つかりませんでした")
        print(f"（min_score={min_score}を下げて再実行してみてください）")


if __name__ == '__main__':
    import sys
    min_score = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    run(min_score)
