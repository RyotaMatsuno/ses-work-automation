"""canonical_audit.py — canonical_skills 533件のゴミ混入 dry-run 調査。

ルールベース分類のみ（LLM禁止）。skill_aliases.json は読み取り専用。
出力: tools/output/canonical_audit_report.md
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parents[1]
SES_WORK = BASE_DIR.parent
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
ALIASES_PATH = BASE_DIR / "skill_aliases.json"
DENYLIST_PATH = BASE_DIR / "denylist.json"
ENGINEERS_PATH = SES_WORK / "poc_engineers.json"
STRUCTURED_PATH = BASE_DIR / "logs" / "structured.jsonl"
REPORT_PATH = OUTPUT_DIR / "canonical_audit_report.md"

JST = timezone(timedelta(hours=9))

# ── 分類ルール定数（alias_filter / skill_gate と整合） ─────────────

_JP_CHAR_RE = re.compile(r"[぀-ヿ一-鿿ｦ-ﾟ]")

_ROLE_CERT_EXACT = frozenset(
    {
        "PM", "PL", "SE", "QA", "PMO", "DBA", "SRE", "RPA",
        "PL経験", "PM経験",
    }
)

_R6_EXTRA = frozenset(
    ["sre", "pmo", "dba", "qa", "se", "pm", "pl", "rpa", "cto", "cfo", "coo", "ceo"]
)

_DANGER_ROLE_PROCESS = frozenset(
    [
        "設計", "開発", "経験", "テスト", "構築", "運用",
        "開発経験", "運用経験", "運用保守", "進捗管理", "構築経験",
        "コミュニケーション力", "主体性", "リーダー", "調整", "実施", "実行", "メール",
        "営業", "ディレクション", "上流工程", "ログ", "SE", "PL", "PM",
    ]
)

_JP_PROCESS_ROLE = frozenset(
    [
        "要件定義", "基本設計", "詳細設計", "設計", "構築", "進捗管理", "ディレクション",
        "上流工程", "上流工程 開発経験", "運用保守", "開発経験", "運用経験", "構築経験",
        "コミュニケーション", "コミュニケーション力", "主体性", "リーダー", "調整",
        "実施", "実行", "メール", "営業", "ログ", "テスト",
        "インフラエンジニア", "フィールドプランナー", "プリセールス", "人材採用",
        "採用人事", "採用人事業務", "営業部門業務", "業務推進", "顧客折衝",
        "スタートアップ業務", "生成AI業務", "AIサービス業務", "ec系業務",
        "金融業界業務", "金融商品取引経験",
    ]
)

_JP_DOMAIN_KEYWORDS = (
    "インフラ", "ネットワーク", "クラウド", "サーバ", "データベース", "セキュリティ",
    "ストレージ", "ファイアウォール", "ロードバランサー", "冗長化", "バッチ",
    "監視", "認証", "認可", "機械学習", "生成AI", "ヘルプデスク", "医事会計",
    "電子カルテ", "メールセキュリティ", "監視ツール", "社内ツール", "データ基盤",
    "データマッピング", "データモデリング", "データ前処理", "マイクロセグメンテーション",
    "リモート接続", "例外処理", "実行環境", "関数", "スクリプト", "ジョブ",
    "サイドカー", "モデル管理", "運用設計", "システム保守", "バックエンド",
    "ネットワークプロトコル", "ネットワーク冗長化", "ネットワーク技術",
    "ネットワーク構築", "ネットワーク設計", "ネットワーク運用",
    "バッチ処理", "バッチ開発", "単体テスト", "テスト設計",
    "IT資産管理", "海外対応", "楽天",
)

_EN_COMMON_WORDS = frozenset(
    [
        "company", "personnel", "database", "basis", "access", "office",
        "details", "participant", "settlement", "experience", "operations",
        "promotion", "construction", "consumer", "general", "professional",
        "social", "worker", "satellite", "shift", "example", "insurance",
        "life", "telecommunications", "industry", "site", "content", "creator",
        "coordination", "negotiation", "availability", "attendance", "presence",
        "management", "behavior", "practitioner", "hourly", "parallel", "status",
        "remote", "work", "business", "user", "clerical", "proactive", "self",
        "senior", "long", "term", "project", "interview", "onsite", "kitting",
        "positive", "ad", "hoc",
    ]
)

_EN_SUSPECT_EXACT = frozenset(
    [
        "Company", "Personnel", "Project Details", "Long-term Participant",
        "RemoteWork", "GS21", "BusinessUser", "AttendanceRecord",
        "ClericalExperience", "InterviewAvailability", "OfficeAttendance",
        "OnSitePresence", "OnSiteWork", "ProactiveBehavior", "ParallelStatus",
        "Hourly Settlement", "Shift Example", "Self-management", "Senior Practitioner",
        "Social Worker", "Satellite Office", "POSITIVE", "Ad-hoc",
        "Construction Industry Experience", "Construction Site Experience",
        "Consumer Content Creator", "Customer Coordination Experience",
        "Customer Negotiation Experience", "General Professional Experience",
        "Life Insurance Experience", "Life Insurance Operations",
        "Operations Experience", "Promotion Experience",
        "Telecommunications Experience", "PC Kitting Experience",
    ]
)

_TECH_PREFIX_RE = re.compile(
    r"^(aws|azure|gcp|google|microsoft|oracle|vmware|cisco|sap|ibm|"
    r"red hat|palo alto|forti|dynamics|firebase|salesforce|"
    r"active|adobe|visual|power|git|node|react|spring|kubernetes|docker|"
    r"apache|nginx|elastic|mongo|postgres|mysql|redis|kafka|terraform|"
    r"ansible|jenkins|grafana|prometheus|datadog|splunk|tableau|"
    r"android|ios|flutter|kotlin|swift|typescript|javascript|python|java|"
    r"ruby|php|perl|rust|go|scala|dart|vue|angular|next|nuxt|nest|"
    r"hubspot|servicenow|snowflake|databricks|airflow|langchain|"
    r"claude|copilot|cursor|figma|unity|unreal|electron|graphql|"
    r"exchange|sharepoint|intune|entra|office|windows|linux|macos|"
    r"vmware|nutanix|cato|aruba|zabbix|looker|marketo|pardot|"
    r"informatica|talend|mulesoft|ui\s*path|playwright|cypress|"
    r"selenium|jest|junit|mockito|gradle|maven|hibernate|mybatis|"
    r"struts|laravel|django|flask|fastapi|express|webpack|vite|"
    r"istio|linkerd|envoy|helm|pulumi|puppet|chef|crossplane|"
    r"ldap|oauth|openapi|protobuf|grpc|websocket|ftp|sftp|dns|"
    r"etl|cdc|dwh|iaas|saas|paas|devops|ci/?cd|cli|vba|"
    r"asteria|intramart|kintone|backlog|confluence|jira|slack|"
    r"genesis|genesys|eloqua|qlik|kyriba|hennge|jamf|tanium|"
    r"checkmarx|sonarqube|fortigate|firewall|router|switch|"
    r"autosar|rexx|clist|cobol|abap|basis|hana|msgtbl|"
    r"netview|websphere|weblogic|tomcat|jboss|jetty|"
    r"corenfc|localauthentication|aidrivendevelopment|serverlessdevelopment|"
    r"apid evelopment|apigateway|geminiapi|generativeai|visualstudiocode|"
    r"cleanarchitecture|authconductor|sapbtp|sapsolutionmanager|ibmzos|"
    r"addresslook|dataspider|dr\.sum|easyplus|grandit|hulft|"
    r"jobcenter|lanscope|lifekeeper|oanda|positive|skysea|ssvc|"
    r"systemwalker|touchdesigner|tricentis|winactor|windchill|vxrail|"
    r"zeroetl|zscaler|blueprint|soc|pcセットアップ)",
    re.IGNORECASE,
)

_TECH_SUFFIX_RE = re.compile(
    r"(?:\.js|\.net|sql|db|api|sdk|os|mq|cd|ci|ml|ai|ui|ux|"
    r"cloud|stack|kit|hub|lab|ops|sec|ssh|vpn|wan|lan|nfc|"
    r"server|service|platform|framework|engine|studio|code|"
    r"script|shell|batch|report|gate|guard|watch|flow|pipe|"
    r"store|cache|queue|stream|spark|torch|chain|agent|"
    r"formation|function|lambda|blob|repo|mesh|proxy|"
    r"center|manager|director|online|desktop|mobile|native)$",
    re.IGNORECASE,
)

_CAMEL_CASE_RE = re.compile(r"^[A-Z][a-z]+(?:[A-Z][a-z]+)+$")
_TITLE_MULTI_RE = re.compile(r"^[A-Z][a-z]+(?:[- ][A-Za-z0-9/+.]+)+$")
_VERSION_RE = re.compile(r"\d")
_CAMEL_NON_TECH_RE = re.compile(
    r"(?:Record|Experience|Availability|Attendance|Presence|Behavior|"
    r"Participant|Details|Settlement|Worker|Practitioner|Status|User|Work|"
    r"Management|Coordination|Negotiation|Promotion|Operations|Insurance|"
    r"Construction|Consumer|Professional|General|Clerical|Remote|Office|"
    r"OnSite|Interview|Parallel|Hourly|Shift|Positive|Business|Proactive|"
    r"Self|Senior|Long|Project|Personnel|Company|Social|Satellite|Kitting)",
)

_CLOUD_CHILD_RE = re.compile(
    r"^(AWS|Azure|GCP|Google|Microsoft|Oracle|SAP|Cisco|VMware|Firebase|"
    r"Dynamics|Salesforce|Service|Financial|Genesys|NEC|Red Hat|Palo Alto|"
    r"Prisma|Power|FortiGate|Direct Connect|Exchange|Adobe|Avaya|"
    r"IdentityNow|SailPoint|UiPath|New Relic|SAP S/4HANA)",
    re.IGNORECASE,
)


def _is_jp(text: str) -> bool:
    return bool(_JP_CHAR_RE.search(text))


def _load_denylist_flat() -> frozenset[str]:
    if not DENYLIST_PATH.exists():
        return frozenset()
    data = json.loads(DENYLIST_PATH.read_text(encoding="utf-8"))
    words: set[str] = set()
    if isinstance(data, list):
        for w in data:
            words.add(str(w).strip().lower())
    else:
        for vals in data.values():
            for w in vals:
                words.add(str(w).strip().lower())
    return frozenset(words)


def _norm_key(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).lower().split())


def _looks_like_tech(name: str) -> bool:
    """英語系 canonical が技術名らしいかのヒューリスティック。"""
    if _TECH_PREFIX_RE.search(name):
        return True
    if _TECH_SUFFIX_RE.search(name.replace(" ", "").replace("-", "")):
        return True
    if _CLOUD_CHILD_RE.match(name):
        return True
    if _VERSION_RE.search(name):
        return True
    # all-caps acronym (2+ chars, not pure digits)
    stripped = name.replace(" ", "").replace("-", "").replace("/", "")
    if stripped.isupper() and len(stripped) >= 2 and any(c.isalpha() for c in stripped):
        if stripped not in {"GS21", "CRQ", "POSITIVE", "SU53", "CVSS", "GRC", "IGA"}:
            return True
    # dotted tech names
    if "." in name and not name.endswith("."):
        return True
    # hash langs
    if name in {"C#", "C++", "C/C++", "F#"}:
        return True
    # known single-word tech products
    known = {
        "Java", "Python", "PHP", "Ruby", "Go", "Rust", "Scala", "Kotlin", "Swift",
        "React", "Angular", "Vue.js", "Docker", "Kubernetes", "Terraform", "Ansible",
        "Jenkins", "Git", "Linux", "Windows", "Oracle", "MySQL", "PostgreSQL",
        "MongoDB", "Redis", "Kafka", "Elasticsearch", "Snowflake", "Databricks",
        "Salesforce", "HubSpot", "ServiceNow", "Figma", "Tableau", "Splunk",
        "Datadog", "Grafana", "Prometheus", "Airflow", "Flutter", "Electron",
        "TypeScript", "JavaScript", "Node.js", "Next.js", "Nuxt.js", "NestJS",
        "Spring", "Django", "Flask", "FastAPI", "Laravel", "Express", "Bootstrap",
        "Selenium", "Cypress", "Playwright", "JUnit", "Jest", "Mockito",
        "Hibernate", "MyBatis", "Struts", "Tomcat", "JBoss", "nginx", "Apache",
        "Cassandra", "DynamoDB", "Hive", "HBase", "Presto", "BigQuery", "Looker",
        "PowerBI", "PowerShell", "Shell", "Cron", "FTP", "SFTP", "DNS", "NAT",
        "LDAP", "OAuth", "HTML", "CSS", "JSON", "CSV", "XML", "YAML",
        "COBOL", "ABAP", "REXX", "CLIST", "Perl", "Dart", "MATLAB", "TensorFlow",
        "PyTorch", "LangChain", "AutoGPT", "Claude", "Copilot", "Cursor", "Codex",
        "OpenCV", "OpenShift", "OpenStack", "OpenAPI", "GraphQL", "gRPC",
        "Firebase", "Heroku", "Backlog", "Confluence", "Jira", "Slack", "Redmine",
        "GitHub", "GitLab", "Bitbucket", "Gradle", "Maven", "Helm", "Pulumi",
        "Puppet", "Chef", "Crossplane", "Istio", "Linkerd", "Envoy", "Fluentd",
        "Logstash", "Kibana", "Zabbix", "Datadog", "New Relic", "Tanium", "Jamf",
        "FortiGate", "Aruba", "Cato", "Nutanix", "VMware", "VxRail", "RHEL",
        "AIX", "UNIX", "macOS", "iOS", "Android", "Unity", "Unreal Engine",
        "Shopify", "WordPress", "Access", "Excel", "Word", "PowerPoint", "Outlook",
        "OneNote", "SharePoint", "Exchange", "Outlook", "Illustrator", "Photoshop",
        "Creo", "Windchill", "Informatica", "Talend", "MuleSoft", "UiPath",
        "WinActor", "kintone", "IntraMart", "ASTERIA Warp", "Dataspider",
        "SAP", "HANA", "Basis", "BizTalk", "Dynamics", "Eclipse", "NetView",
        "WebSphere", "WebLogic", "WebSocket", "Webpack", "Vite", "Vitest",
        "Thymeleaf", "Seasar2", "MySQL", "Db2", "RDBMS", "ETL", "CDC", "DWH",
        "IaaS", "SaaS", "PaaS", "ML", "LLM", "AI", "API", "CLI", "VBA",
        "A10", "ADDS", "ADFS", "AUTOSAR", "Argo CD", "ActiveMQ", "Active Directory",
        "Adobe Creative Cloud", "Avaya PBX", "AWS", "Azure", "GCP", "OCI",
        "EC2", "Lambda", "MQ", "RTOS", "SASE", "SD-WAN", "OSPF", "VSAM",
        "MSGTBL", "JP1", "HULFT", "GRANDIT", "EASYPLUS", "LANSCOPE", "SKYSEA",
        "Systemwalker", "HENNGE", "Kyriba", "OANDA", "freee", "GA4",
        "L2Support", "L3Support", "LAMP", "MVVM", "UIKit", "SwiftUI",
        "BluePrint", "Blueprint", "SOC", "GRC", "IGA", "CVSS", "CRQ",
        "In-vehicle", "eKYC SDK", "CoreNFC", "LocalAuthentication",
        "NVIDIA", "TouchDesigner", "Speaker Deck", "Pardot", "Marketo",
        "Eloqua", "Qlik", "QuickSight", "TestRail", "SonarQube", "Checkmarx",
        "SCCM", "IdentityNow", "SailPoint", "Genesys Cloud", "Financial Service Cloud",
        "Service Cloud", "Platform App Builder", "Visualforce", "Dataverse",
        "SOC", "HULFT", "SKYSEA", "HENNGE", "LAMP", "RDBMS", "IIS", "MATLAB",
        "VB6", "A10", "DS8000", "OANDA",
        "Power Apps", "Power Automate", "Power Automate Desktop", "Power BI",
        "Power Platform", "PowerScale", "Microsoft 365", "Microsoft Access",
        "Microsoft Dynamics 365", "Microsoft Entra ID", "Microsoft Intune",
        "Microsoft Office", "Microsoft SQL Server", "MS SQL Server", "SQL Server",
        "Google AppSheet", "Google Workspace", "Oracle Cloud", "Oracle Linux",
        "AWS Aurora", "AWS CDK", "AWS ECS", "AWS Fargate", "AWS Lambda", "AWS S3",
        "Azure Blob", "Azure DevOps", "Azure Repos", "Dynamics 365", "Dynamics 365 FO",
        "Firebase Cloud Messaging", "Cisco Catalyst", "Cisco Umbrella",
        "Palo Alto Networks", "Prisma Access", "Red Hat", "Red Hat Linux",
        "VMware ESXi", "VMware NSX", "VMware vCenter", "VMware vSphere",
        "NEC IX", "FI-AA", "FI-AP", "FI-AR", "FI-GL", "PFCG", "SAP FI",
        "SAP S/4HANA", "SAPBTP", "SAPSolutionManager", "IBMzOS", "DS8000",
        "Dr.Sum", "Dataspider Servista", "JasperReports", "IntelliJ IDEA",
        "Visual Studio", "Visual Studio 2022", "Visual Studio Code", "VisualStudioCode",
        "Access VBA", "Excel VBA", "Exchange Online", "Direct Connect",
        "Claude Code", "AI Agent", "AIDrivenDevelopment", "APIDevelopment",
        "APIGateway", "GeminiAPI", "GenerativeAI", "ServerlessDevelopment",
        "AuthConductor", "CleanArchitecture", "Tectia SSH", "LDAP Manager",
        "Tricentis qTest", "Jobcenter", "LifeKeeper", "V-Recover", "SSVC",
        "JP1/AJ", "JP1/AJS3", "React Native", "Ruby on Rails", "Unreal Engine",
        "VB.NET", "VB6", "PL/SQL", ".NET", ".NET Core",
    }
    if name in known:
        return True
    lower = name.lower()
    if lower in {
        "php", "css", "sql", "c#", "c++", "vba", "etl", "vue3", "css3",
        "html", "jsp", "json", "xml", "yaml", "git", "svn", "cvs",
        "dbt", "rpa", "sre", "dba", "pmo", "qa",
    }:
        return True
    return False


def classify_canonical(name: str, denylist: frozenset[str]) -> tuple[str, str]:
    """(category, reason) — category in tech/domain_jp/suspect/role_cert。"""
    lower = name.lower()
    norm = _norm_key(name)

    # ── role_cert ──
    if name in _ROLE_CERT_EXACT or lower in _R6_EXTRA:
        return "role_cert", "職種略語(R6)"
    if name in _DANGER_ROLE_PROCESS:
        return "role_cert", "プロセス/職務語(DANGER系)"
    if name in _JP_PROCESS_ROLE:
        return "role_cert", "和文プロセス/職務語"
    if lower in denylist:
        return "role_cert", "denylist該当"
    if _is_jp(name) and name.endswith("経験"):
        return "role_cert", "和文〜経験（プロセス/職務）"
    if _is_jp(name) and name.endswith("業務"):
        if not any(kw in name for kw in ("AI", "生成", "セキュリティ", "ネットワーク", "クラウド")):
            return "role_cert", "和文〜業務（非技術領域）"
    if _is_jp(name) and name.endswith("エンジニア"):
        return "role_cert", "職種名(〜エンジニア)"
    if _is_jp(name) and name.endswith("開発") and name not in {
        "Android開発", "iOS開発", "Web開発", "WEBアプリケーション開発",
        "バックエンド開発", "システム保守開発",
    }:
        pass  # fall through — バッチ開発 etc. handled by domain_jp

    # ── domain_jp ──
    if _is_jp(name):
        if any(kw in name for kw in _JP_DOMAIN_KEYWORDS):
            return "domain_jp", "和文技術領域キーワード"
        if name in {
            "Android開発", "iOS開発", "Web開発", "WEBアプリケーション開発",
            "バックエンド開発", "システム保守開発", "バッチ開発", "C言語",
            "UI/UXデザイン", "サイボウズ Office", "生成AI", "機械学習",
        }:
            return "domain_jp", "和文技術開発領域"

    # ── suspect (英語系ノイズ) ──
    if name in _EN_SUSPECT_EXACT:
        return "suspect", "既知ノイズ(手動リスト)"
    if _looks_like_tech(name):
        return "tech", "技術名ヒューリスティック"
    if _CAMEL_CASE_RE.match(name) and _CAMEL_NON_TECH_RE.search(name):
        if not _looks_like_tech(name):
            return "suspect", "CamelCase非技術複合語"
    if " Experience" in name or name.endswith("Experience"):
        if not _looks_like_tech(name):
            return "suspect", "英語Experience句（業務経験ノイズ）"
    if _TITLE_MULTI_RE.match(name):
        words = re.split(r"[\s\-/]+", name.lower())
        common_hits = [w for w in words if w in _EN_COMMON_WORDS]
        if common_hits and not _looks_like_tech(name):
            return "suspect", f"英語一般語含む({','.join(common_hits[:3])})"
    # short unknown code
    if re.match(r"^[A-Z]{1,2}\d{2,}$", name):
        return "suspect", "意味不明コード"
    if re.match(r"^[A-Z0-9]{2,6}$", name) and name not in {
        "AWS", "GCP", "OCI", "API", "CLI", "CSS", "CSV", "CDC", "DWH",
        "ETL", "FTP", "DNS", "NAT", "MQ", "ML", "LLM", "AI", "SAP",
        "PHP", "SQL", "VBA", "RPA", "SRE", "DBA", "PMO", "QA", "SE",
        "PL", "PM", "ADDS", "ADFS", "AIX", "A10", "COBOL", "ABAP",
        "REXX", "CLIST", "HANA", "GRC", "IGA", "CVSS", "CRQ", "SU53",
        "RTOS", "SASE", "OSPF", "VSAM", "EC2", "GA4", "IaaS", "SaaS",
        "MVVM", "RHEL", "UNIX", "HTML", "JSON", "JSP", "LDAP",
        "OAuth", "SFTP", "SSVC", "MSGTBL", "JP1", "FI-AA", "FI-AP",
        "FI-AR", "FI-GL", "PFCG", "DS8000", "IBMzOS", "SAPBTP",
        "SOC", "HULFT", "SKYSEA", "HENNGE", "LAMP", "RDBMS", "IIS",
        "SCCM", "VB6", "OANDA",
    }:
        return "suspect", "短略語(技術未確認)"
    if lower in _EN_COMMON_WORDS:
        return "suspect", "英語一般語"

    # ── tech / domain_jp (default) ──
    if _is_jp(name):
        return "domain_jp", "和文(技術領域デフォルト)"
    return "tech", "デフォルト(tech)"


def _build_alias_index(aliases_data: dict) -> dict[str, list[str]]:
    """canonical -> [alias keys]"""
    index: dict[str, list[str]] = defaultdict(list)
    for key, canonical in aliases_data.get("aliases", {}).items():
        index[canonical].append(key)
    return dict(index)


def _load_normalizer():
    if str(BASE_DIR) not in sys.path:
        sys.path.insert(0, str(BASE_DIR))
    from matcher import SkillNormalizer

    return SkillNormalizer(ALIASES_PATH)


def _collect_tokens(engineers_path: Path, structured_path: Path) -> list[tuple[str, str]]:
    tokens: list[tuple[str, str]] = []
    if structured_path.exists():
        with structured_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                for bucket in ("required_skills", "optional_skills", "ambiguous_skills"):
                    for s in row.get(bucket) or []:
                        t = str(s).strip()
                        if t:
                            tokens.append((t, "案件"))
    if engineers_path.exists():
        data = json.loads(engineers_path.read_text(encoding="utf-8"))
        for eng in data:
            raw = eng.get("skills") or eng.get("スキル") or ""
            if isinstance(raw, str):
                parts = [p.strip() for p in raw.replace("/", ",").split(",") if p.strip()]
            else:
                parts = [str(p).strip() for p in raw]
            for s in parts:
                if s:
                    tokens.append((s, "人材"))
    return tokens


def _count_refs(
    canonical: str,
    alias_keys: list[str],
    tokens: list[tuple[str, str]],
    normalizer,
) -> dict[str, int]:
    """canonical へのマッチング参照回数（案件/人材別）。"""
    counts: Counter[str] = Counter()
    targets = {canonical.lower()}
    targets.update(k.lower() for k in alias_keys)
    targets_norm = {_norm_key(t) for t in targets}

    for raw, source in tokens:
        resolved = normalizer.resolve_canonical(raw)
        if resolved == canonical:
            counts[source] += 1
            continue
        raw_norm = _norm_key(raw)
        if raw_norm in targets_norm or raw.lower() in targets:
            counts[source] += 1
    return dict(counts)


def _impact_assessment(engineer_hits: int, case_hits: int) -> str:
    total = engineer_hits + case_hits
    if total == 0:
        return "影響なし（参照0）— 削除してもマッチング影響ほぼ無し"
    if total <= 2:
        return f"低影響（計{total}件）— 限定的なエイリアス経由ヒット"
    if case_hits == 0 and engineer_hits > 0:
        return f"人材側のみ（計{total}件）— エンジニアDB表記ゆれ吸収に使用中"
    if engineer_hits == 0 and case_hits > 0:
        return f"案件側のみ（計{total}件）— 案件スキル抽出ノイズ源の可能性"
    return f"中影響（計{total}件）— 人材{engineer_hits}+案件{case_hits}、削除前にエイリアス移行要検討"


def _r16_root_cause_note() -> str:
    return (
        "R16は「aliasのcanonical値が canonical_skills リストに存在するか」のみを検証する。"
        "canonical_skills 自体の品質（非スキル語かどうか）は検査対象外のため、"
        "Company / RemoteWork 等がリストに登録されている限り、関連aliasはR16を素通りする。"
    )


def run_audit() -> Path:
    aliases_data = json.loads(ALIASES_PATH.read_text(encoding="utf-8"))
    canonical_skills: list[str] = list(aliases_data.get("canonical_skills", []))
    denylist = _load_denylist_flat()
    alias_index = _build_alias_index(aliases_data)
    tokens = _collect_tokens(ENGINEERS_PATH, STRUCTURED_PATH)
    normalizer = _load_normalizer()

    classified: dict[str, list[dict]] = {
        "tech": [],
        "domain_jp": [],
        "suspect": [],
        "role_cert": [],
    }

    for name in canonical_skills:
        cat, reason = classify_canonical(name, denylist)
        entry: dict = {"name": name, "reason": reason, "aliases": alias_index.get(name, [])}
        if cat in ("suspect", "role_cert"):
            refs = _count_refs(name, entry["aliases"], tokens, normalizer)
            eng = refs.get("人材", 0)
            case = refs.get("案件", 0)
            entry["refs_engineer"] = eng
            entry["refs_case"] = case
            entry["refs_total"] = eng + case
            entry["impact"] = _impact_assessment(eng, case)
        classified[cat].append(entry)

    now = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    lines: list[str] = [
        "# canonical_skills ゴミ混入 dry-run 調査レポート",
        "",
        f"生成日時: {now}",
        f"対象: `skill_aliases.json` canonical_skills **{len(canonical_skills)}件**",
        "分類方式: ルールベースのみ（LLM未使用）",
        "",
        "## サマリ",
        "",
        "| 分類 | 件数 | 説明 |",
        "|------|------|------|",
        f"| tech | {len(classified['tech'])} | 明確な技術名 |",
        f"| domain_jp | {len(classified['domain_jp'])} | 和文技術領域（インフラ/ネットワーク等）→ 残す |",
        f"| suspect | {len(classified['suspect'])} | 非スキル疑い（英語一般語・文断片・意味不明） |",
        f"| role_cert | {len(classified['role_cert'])} | 職種・資格・プロセス語（禁止ポリシー対象） |",
        "",
        "## R16 素通りの根本原因",
        "",
        _r16_root_cause_note(),
        "",
        f"参照データ: `{ENGINEERS_PATH.name}` ({_count_engineers(ENGINEERS_PATH)}名), "
        f"`{STRUCTURED_PATH.relative_to(BASE_DIR)}` ({_count_cases(STRUCTURED_PATH)}件)",
        "",
    ]

    for section, title in [
        ("suspect", "suspect 全件リスト"),
        ("role_cert", "role_cert 全件リスト"),
    ]:
        items = sorted(classified[section], key=lambda x: (-x.get("refs_total", 0), x["name"]))
        lines += [
            f"## {title}（{len(items)}件）",
            "",
            "| canonical | 判定理由 | 人材参照 | 案件参照 | 合計 | 削除影響見立て | エイリアス数 |",
            "|-----------|----------|----------|----------|------|----------------|-------------|",
        ]
        for e in items:
            alias_n = len(e["aliases"])
            lines.append(
                f"| {e['name']} | {e['reason']} | {e.get('refs_engineer', 0)} | "
                f"{e.get('refs_case', 0)} | {e.get('refs_total', 0)} | {e.get('impact', '')} | {alias_n} |"
            )
        lines.append("")

    # suspect + role_cert 影響集計
    flagged = classified["suspect"] + classified["role_cert"]
    zero_ref = sum(1 for e in flagged if e.get("refs_total", 0) == 0)
    with_ref = len(flagged) - zero_ref
    total_eng = sum(e.get("refs_engineer", 0) for e in flagged)
    total_case = sum(e.get("refs_case", 0) for e in flagged)

    lines += [
        "## 削除影響サマリ（suspect + role_cert）",
        "",
        f"- フラグ計: **{len(flagged)}件**（suspect {len(classified['suspect'])} + role_cert {len(classified['role_cert'])}）",
        f"- 参照0（削除影響ほぼ無し）: **{zero_ref}件**",
        f"- 参照あり（要移行検討）: **{with_ref}件**",
        f"- 人材DB参照合計: {total_eng} / 案件キャッシュ参照合計: {total_case}",
        "",
        "## 推奨アクション（dry-run・未実施）",
        "",
        "1. suspect {0}件: canonical_skills からの除外候補。参照ありはエイリアス先の再マッピング後に削除。".format(
            len(classified["suspect"])
        ),
        "2. role_cert {0}件: process_skills / denylist 側で処理済みか確認し、canonical からは段階的に除外。".format(
            len(classified["role_cert"])
        ),
        "3. R16強化案: canonical_skills 登録時に本スクリプト同等のルールベース分類をゲートに追加。",
        "",
        "## domain_jp 一覧（参考・残す対象）",
        "",
    ]
    for e in sorted(classified["domain_jp"], key=lambda x: x["name"]):
        lines.append(f"- {e['name']} — {e['reason']}")
    lines.append("")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    return REPORT_PATH


def _count_engineers(path: Path) -> int:
    if not path.exists():
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    return len(data) if isinstance(data, list) else 0


def _count_cases(path: Path) -> int:
    if not path.exists():
        return 0
    n = 0
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                n += 1
    return n


def main() -> None:
    report = run_audit()
    print(f"レポート生成: {report}")
    data = json.loads(ALIASES_PATH.read_text(encoding="utf-8"))
    n = len(data.get("canonical_skills", []))
    print(f"canonical_skills: {n}件を分類完了")


if __name__ == "__main__":
    main()
