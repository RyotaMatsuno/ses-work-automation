# matching_v2.pyにプレフィルタを追加するパッチ
path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\matching_v2.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. プレフィルタ関数を追加（import requestsの後に挿入）
prefilter_code = '''

# --------------- プレフィルタ（APIコール削減用） ---------------
# 案件のスキル要件からキーワードを抽出し、エンジニアのスキルリスト/raw_text/skill_textに
# 1つでも部分一致するものだけを候補として残す。
# これによりAPIコール数を大幅に削減する。

_SKILL_ALIASES = {
    "java": ["java", "spring", "springboot", "struts"],
    "python": ["python", "django", "flask", "fastapi"],
    "javascript": ["javascript", "js", "typescript", "ts", "react", "vue", "angular", "node"],
    "c#": ["c#", "csharp", ".net", "asp.net"],
    "php": ["php", "laravel", "cakephp", "symfony"],
    "ruby": ["ruby", "rails", "ror"],
    "go": ["go", "golang"],
    "aws": ["aws", "amazon", "ec2", "s3", "lambda", "ecs", "fargate"],
    "azure": ["azure", "microsoft cloud"],
    "gcp": ["gcp", "google cloud", "bigquery"],
    "sql": ["sql", "oracle", "mysql", "postgresql", "postgres", "sqlserver", "db2"],
    "sap": ["sap", "abap", "s/4hana", "s4hana"],
    "salesforce": ["salesforce", "sfdc", "apex"],
    "pmo": ["pmo", "プロジェクトマネジメント", "プロジェクト管理"],
    "pm": ["pm", "プロジェクトマネージャ", "プロマネ"],
    "インフラ": ["インフラ", "infrastructure", "linux", "windows server", "vmware", "docker", "kubernetes", "k8s"],
    "ネットワーク": ["ネットワーク", "network", "cisco", "firewall", "vpn", "l2", "l3"],
    "セキュリティ": ["セキュリティ", "security", "soc", "csirt", "isms"],
    "テスト": ["テスト", "test", "qa", "品質"],
    "cobol": ["cobol"],
    "rpg": ["rpg", "as400", "ibm i"],
    "swift": ["swift", "ios"],
    "kotlin": ["kotlin", "android"],
    "flutter": ["flutter", "dart"],
    "react": ["react", "next.js", "nextjs"],
    "vue": ["vue", "nuxt", "nuxtjs"],
    "angular": ["angular"],
}

def _extract_keywords_from_skills(skill_names):
    """スキル名リストから検索キーワードリストを生成"""
    keywords = set()
    for skill in skill_names:
        skill_lower = skill.lower().strip()
        keywords.add(skill_lower)
        # エイリアスマッチ
        for base, aliases in _SKILL_ALIASES.items():
            if any(alias in skill_lower for alias in aliases):
                keywords.update(aliases)
    return keywords

def _engineer_text_blob(engineer):
    """エンジニアの全テキスト情報を1つの小文字文字列に結合"""
    parts = []
    parts.extend(engineer.get("skills", []))
    parts.append(engineer.get("raw_text", ""))
    parts.append(engineer.get("raw_body", ""))
    return " ".join(parts).lower()

def prefilter_engineers(project, engineers):
    """
    案件のスキル要件に基づいてエンジニアをキーワード事前フィルタする。
    必須スキルのキーワードが1つでもエンジニアのテキストに含まれれば候補に残す。
    スキル要件なしの場合は全員返す。
    """
    required = project.get("required_skills", [])
    optional = project.get("optional_skills", [])
    all_skills = required + optional
    if not all_skills:
        return engineers

    keywords = _extract_keywords_from_skills(all_skills)
    if not keywords:
        return engineers

    filtered = []
    for eng in engineers:
        blob = _engineer_text_blob(eng)
        if any(kw in blob for kw in keywords):
            filtered.append(eng)
    return filtered
# --------------- プレフィルタここまで ---------------
'''

# import requests の後に挿入
insert_point = "import requests\n"
if insert_point in content:
    content = content.replace(insert_point, insert_point + prefilter_code, 1)

# 2. mainループ内でprefilterを使う
# "print(f\"判定中: {project['name']}（{len(engineers)}名）\", flush=True)" の前にフィルタを挿入
old_line = "        print(f\"判定中: {project['name']}（{len(engineers)}名）\", flush=True)"
new_lines = """        # プレフィルタでAPI対象を絞る
        filtered_engineers = prefilter_engineers(project, engineers)
        print(f"判定中: {project['name']}（フィルタ後: {len(filtered_engineers)}/{len(engineers)}名）", flush=True)
        
        if not filtered_engineers:
            print(f"  → プレフィルタで候補0名、スキップ", flush=True)
            projects_results.append({
                "project": project,
                "candidates": candidates,
            })
            output_projects.append(make_project_result(project, candidates))
            continue"""

if old_line in content:
    content = content.replace(old_line, new_lines, 1)

# 3. judge_with_cache に渡す engineers を filtered_engineers に変更
old_judge = """        batch_judgement = judge_with_cache(
            cache,
            cache_lock,
            project["required_skills"],
            project["optional_skills"],
            engineers,
        )"""
new_judge = """        batch_judgement = judge_with_cache(
            cache,
            cache_lock,
            project["required_skills"],
            project["optional_skills"],
            filtered_engineers,
        )"""

if old_judge in content:
    content = content.replace(old_judge, new_judge, 1)

# 4. evaluate_candidate のループも filtered_engineers に（ただし全engineersでスコア出すため元のまま）
# 実際にはbatch_judgementに結果があるエンジニアしか評価できないので問題なし
# ただし全engineersをループしてもjudgementがempty dictだとスコア0になるので
# filtered_engineersだけをループする方が効率的
old_futures = """            for engineer in engineers:
                judgement = batch_judgement.get(engineer["name"], {})
                futures.append(executor.submit(
                    evaluate_candidate,
                    project,
                    engineer,
                    judgement,
                ))"""
new_futures = """            for engineer in filtered_engineers:
                judgement = batch_judgement.get(engineer["name"], {})
                futures.append(executor.submit(
                    evaluate_candidate,
                    project,
                    engineer,
                    judgement,
                ))"""

if old_futures in content:
    content = content.replace(old_futures, new_futures, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("patch applied successfully")
