import sys

sys.stdout.reconfigure(encoding="utf-8")

IMP = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_attachment_importer"
ai_path = IMP + r"\ai_extractor.py"

with open(ai_path, encoding="utf-8") as f:
    content = f.read()

# バックアップ
with open(ai_path + ".bak_skills", "w", encoding="utf-8") as f:
    f.write(content)

old_skills = """SKILL_OPTIONS = [
    "Java", "Python", "PHP", "JavaScript", "TypeScript", "C#", "Node.js", "React",
    "AWS", "インフラ", "PostgreSQL", "Oracle", "Vue.js", "MySQL", "Swift", "Azure",
    "Linux", "Go", "Ruby", "Docker", "MongoDB", "Spring"
]"""

new_skills = """SKILL_OPTIONS = [
    # 言語
    "Java", "Python", "PHP", "JavaScript", "TypeScript", "C#", "VB.NET", "C", "C++",
    "Go", "Ruby", "Swift", "Kotlin", "Scala", "COBOL", "RPG", "Perl", "R",
    # フレームワーク
    "Spring", "Spring Boot", "Node.js", "React", "Vue.js", "Angular", "Next.js",
    "Django", "Flask", "FastAPI", "Laravel", "Rails", "ASP.NET",
    # クラウド・インフラ
    "AWS", "Azure", "GCP", "インフラ", "Linux", "Windows Server",
    "Docker", "Kubernetes", "Terraform", "Ansible",
    # DB
    "Oracle", "MySQL", "PostgreSQL", "SQL Server", "DB2", "MongoDB", "Redis", "DynamoDB",
    # BI・データ
    "Salesforce", "SAP", "SAP ABAP", "Tableau", "PowerBI", "BigQuery",
    # ネットワーク・セキュリティ
    "ネットワーク", "セキュリティ", "Cisco", "Firewall",
    # その他
    "PMO", "PM", "テスト", "Selenium", "Git", "Jenkins",
]"""

if old_skills in content:
    content = content.replace(old_skills, new_skills, 1)
    with open(ai_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("スキルリスト拡充OK: 22種 → 60種超")
else:
    print("対象が見つかりません")
    # 現状を確認
    start = content.find("SKILL_OPTIONS")
    print(repr(content[start : start + 200]))
