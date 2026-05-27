# SPEC_skill_autofill.md — スキル自動補完機能

## 目的
案件のrequired_skills/optional_skillsが空のとき、
案件詳細テキスト（detail）からClaudeがスキルを抽出し、
NotionのDB（必要スキル・尚可スキル）に書き戻す。

## 対象ファイル
- 追加: `pipeline_v1/skill_autofill.py`
- 修正: `pipeline_v1/fetcher.py` の `fetch_projects()` の後に呼び出し

## 処理フロー
1. `fetch_projects()` の結果を受け取る
2. required_skillsもoptional_skillsも空の案件だけ対象
3. detailテキストをClaudeに渡してスキル抽出（claude-haiku-4-5-20251001）
4. 抽出結果をNotionページにPATCH（必要スキル・尚可スキルに書き込み）
5. projectオブジェクトのrequired_skills/optional_skillsも更新して返す

## Claude呼び出し仕様
```python
system = """SES案件テキストからスキルを抽出してJSON形式で返してください。
Reply JSON only. No markdown.
{"required_skills": ["Java", "Spring Boot"], "optional_skills": ["Docker"]}
スキル名は英語（Java, Python, AWS, Reactなど）で返してください。
不明な場合は空リスト。"""
user = detail_text
```

## Notion PATCH仕様
```python
props = {}
if required_skills:
    props["必要スキル"] = {"multi_select": [{"name": s} for s in required_skills]}
if optional_skills:
    props["尚可スキル"] = {"multi_select": [{"name": s} for s in optional_skills]}
requests.patch(f"https://api.notion.com/v1/pages/{page_id}", headers=headers, json={"properties": props})
```

## VALID_SKILLS（webhook_server.pyと同じリストを使う）
Java, Python, PHP, JavaScript, TypeScript, C#, C++, Go, Ruby, Swift, Kotlin,
React, Vue.js, Angular, Next.js, Node.js, Spring Boot, Django, Flask, Laravel,
AWS, GCP, Azure, Docker, Kubernetes, Linux, MySQL, PostgreSQL, Oracle, SQL Server,
MongoDB, Redis, Git, Terraform, Ansible, Jenkins, Salesforce, SAP, PowerBI,
Tableau, Spark, TensorFlow, CCNA, Cisco

## 関数シグネチャ
```python
def autofill_skills(projects: list[dict], api_key: str) -> list[dict]:
    """スキル空案件のdetailからスキルを抽出してNotionに書き戻し、projectsを更新して返す"""
```

## credential
ENV_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env"
ANTHROPIC_API_KEY = config["ANTHROPIC_API_KEY"]
NOTION_API_KEY = config["NOTION_API_KEY"]

## pipeline.pyへの組み込み
run_pipeline()の中で:
```python
projects = fetch_projects()
projects = autofill_skills(projects, api_key)  # ← ここに追加
engineers = fetch_engineers()
```
