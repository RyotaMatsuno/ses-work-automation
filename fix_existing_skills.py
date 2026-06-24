import json
import re
import sys
import time

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
import requests
from dotenv import dotenv_values

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
notion_token = env.get("NOTION_TOKEN") or env.get("NOTION_API_KEY")
anthropic_key = env.get("ANTHROPIC_API_KEY")
db_id = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"

notion_headers = {
    "Authorization": f"Bearer {notion_token}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

VALID_SKILLS = [
    "Java",
    "Python",
    "PHP",
    "JavaScript",
    "TypeScript",
    "C#",
    "C++",
    "C",
    "Go",
    "Ruby",
    "Swift",
    "Kotlin",
    "R",
    "COBOL",
    "VB.NET",
    "VBA",
    "Scala",
    "Rust",
    "Perl",
    "Bash",
    "React",
    "Vue.js",
    "Angular",
    "Next.js",
    "Nuxt.js",
    "HTML",
    "CSS",
    "jQuery",
    "Node.js",
    "Spring",
    "Spring Boot",
    "Django",
    "Flask",
    "Laravel",
    "Rails",
    ".NET",
    "Express",
    "FastAPI",
    "AWS",
    "GCP",
    "Azure",
    "Docker",
    "Kubernetes",
    "Terraform",
    "Ansible",
    "Linux",
    "Windows Server",
    "VMware",
    "OpenStack",
    "Nginx",
    "Apache",
    "MySQL",
    "PostgreSQL",
    "Oracle",
    "SQL Server",
    "MongoDB",
    "Redis",
    "Elasticsearch",
    "DynamoDB",
    "Cassandra",
    "SQLite",
    "Jenkins",
    "GitLab",
    "GitHub Actions",
    "CircleCI",
    "Git",
    "Jira",
    "Confluence",
    "Tableau",
    "PowerBI",
    "Spark",
    "Hadoop",
    "TensorFlow",
    "PyTorch",
    "scikit-learn",
    "Salesforce",
    "SAP",
    "ServiceNow",
    "SharePoint",
    "Power Apps",
    "Power Automate",
    "CCNA",
    "CCNP",
    "Cisco",
    "Fortinet",
    "Zabbix",
    "Prometheus",
    "FPGA",
    "PLC",
    "Unity",
    "Android Studio",
    "Xcode",
]


def call_claude(text, current_skills):
    """備考テキスト＋現スキルから有効スキルのみ抽出"""
    prompt = f"""あなたはSES業界のスキル分析AIです。
以下の人材の備考テキストと現在登録されているスキルリストを見て、
「直近10年以内（2016年以降）に実際に使用したスキル」のみをJSON配列で返してください。

ルール:
- スキルシートや職歴から最終使用年を推定する
- 2015年以前にしか使っていないスキルは除外
- 経験年数が不明でも職歴に登場していれば含める
- 経験年数の長い順に並べる
- VALID_SKILLSリストの表記に統一する
- JSONのみ返す。マークダウン不要。

VALID_SKILLS: {json.dumps(VALID_SKILLS, ensure_ascii=False)}

現在のスキル: {json.dumps(current_skills, ensure_ascii=False)}

備考テキスト:
{text[:3000]}

出力形式: {{"skills": ["Java", "Spring", ...], "removed": ["C#", ...], "reason": "除外理由の簡単な説明"}}
"""
    res = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": anthropic_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 500,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=30,
    )
    if res.status_code == 200:
        text_out = res.json()["content"][0]["text"]
        try:
            return json.loads(re.sub(r"```json|```", "", text_out).strip())
        except:
            pass
    return None


# 全件取得
results = []
payload = {"page_size": 100}
while True:
    r = requests.post(f"https://api.notion.com/v1/databases/{db_id}/query", headers=notion_headers, json=payload)
    data = r.json()
    results.extend(data.get("results", []))
    if not data.get("has_more"):
        break
    payload["start_cursor"] = data["next_cursor"]

print(f"対象: {len(results)}件")
updated = skipped = errors = 0

for page in results:
    pid = page["id"]
    props = page["properties"]

    name_items = props.get("名前", {}).get("title", [])
    name = name_items[0]["plain_text"] if name_items else "不明"

    current_skills = [o["name"] for o in props.get("スキル", {}).get("multi_select", [])]
    if not current_skills:
        print(f"  [SKIP] {name}: スキルなし")
        skipped += 1
        continue

    # 備考テキスト取得
    note_items = props.get("備考（LINEメモ）", {}).get("rich_text", [])
    note_text = note_items[0]["plain_text"] if note_items else ""

    # テキストが短すぎる場合はスキップ（情報不足）
    if len(note_text.strip()) < 30:
        print(f"  [SKIP] {name}: 備考テキスト不足（{len(note_text)}文字）")
        skipped += 1
        continue

    # Claude APIで再分析
    result = call_claude(note_text, current_skills)
    time.sleep(0.5)  # レート制限対策

    if not result:
        print(f"  [ERROR] {name}: Claude API失敗")
        errors += 1
        continue

    new_skills = result.get("skills", [])
    removed = result.get("removed", [])
    reason = result.get("reason", "")

    if set(new_skills) == set(current_skills):
        print(f"  [NO CHANGE] {name}: 変更なし {current_skills}")
        skipped += 1
        continue

    # Notion更新
    update_payload = {"properties": {"スキル": {"multi_select": [{"name": s} for s in new_skills]}}}
    r2 = requests.patch(f"https://api.notion.com/v1/pages/{pid}", headers=notion_headers, json=update_payload)

    if r2.status_code == 200:
        print(f"  [UPDATED] {name}")
        print(f"    Before: {current_skills}")
        print(f"    After:  {new_skills}")
        if removed:
            print(f"    除外:   {removed} ({reason})")
        updated += 1
    else:
        print(f"  [ERROR] {name}: Notion更新失敗 {r2.status_code}")
        errors += 1

print(f"\n完了: 更新={updated} スキップ={skipped} エラー={errors}")
