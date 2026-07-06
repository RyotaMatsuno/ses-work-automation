# SPEC.md - Engineer DB Quality Improvement Pipeline

## 1. Overview
Notion エンジニアDB（208件）の備考LINEメモ・人員情報原文から
構造化データを抽出し、空欄フィールドを補完するルールベースパイプライン。

## 2. Goals
- スキル空欄35件 → 件名・ラベルから自動補完
- 単価空欄35件 → 件名・ラベルから自動補完  
- 最寄り駅 4/208 → 120+件に改善
- 経験年数 120/208 → 150+件に改善
- 稼働可能日 57/208 → 100+件に改善
- dry-run / shadow / apply の3モード対応
- 誤更新ゼロ（空欄補完のみ）

## 3. Pipeline Architecture

```
Notion DB fetch (全208件)
  ↓
Text source selection (人員情報原文 + 備考LINEメモ)
  ↓
Pattern detection (3パターン判定)
  ↓
Text segmentation (subject / body / labeled_fields 分離)
  ↓
Field extraction (6つの抽出器を並列実行)
  ↓
Merge policy check (空欄のみ更新判定)
  ↓
Report generation (dry-run / shadow / apply)
  ↓
Optional Notion update (--apply時のみ)
```

## 4. Text Parser Design

### 4.1 Pattern Detection
| Pattern | Detection Rule | Priority |
|---------|---------------|----------|
| Pattern 1 (自動取込) | `[自動取込]` を含む | 1 |
| Pattern 2 (メール自動登録) | `【メールから自動登録】` を含む | 2 |
| Pattern 3 (LINE登録) | `[LINE登録:` or `[LINE auto-register:` を含む | 3 |
| Fallback | 上記に該当しない | 4 |

### 4.2 Text Segmentation Output
```python
@dataclass
class ParsedEngineerText:
    pattern_type: str  # "auto_import" | "email_register" | "line_register" | "unknown"
    subject: str | None
    body: str
    labeled_fields: dict[str, str]  # {"単価": "40万円", "スキル": "PHP, Java", ...}
    sender: str | None
    received_date: str | None
    full_text: str
```

### 4.3 Subject Extraction Rules
Pattern 1: `件名:` の後ろのテキスト全体
Pattern 2: `件名:` の後ろのテキスト全体
Pattern 3: なし（labeled_fieldsが主体）

### 4.4 Labeled Fields Extraction
以下のラベルパターンを検出：
- `【スキル】`, `【単価】`, `【最寄】`, `【開始】`, `【名前】`, `【所属】`, `【並行】`, `【資格】`, `【経験】`, `【備考】`
- `スキル：`, `単価：`, `最寄駅：`, `希望単価：`
- `名前`, `性別`, `年齢`, `国籍`, `最寄り駅`, `稼動可能日`

## 5. Field Extractors

### 5.1 Skills Extractor
**Layer 1: Labeled extraction**
- `【スキル】PHP, Java, SQL` → ["PHP", "Java", "SQL"]
- 区切り: `,` `、` `/` `／` `|` `・` 改行

**Layer 2: Subject bracket extraction**
- `【RHEL / CLUSTERPRO / JP1】` → ["RHEL", "CLUSTERPRO", "JP1"]
- `Swift・Kotlin・Java` → ["Swift", "Kotlin", "Java"]

**Layer 3: Dictionary matching**
- skill_dictionary.json に定義された技術用語をテキスト全体から検出
- case-insensitive matching
- 最低200語の初期辞書（主要言語/FW/クラウド/DB/ミドルウェア/ツール）

**Layer 4: Tech-token heuristic**
- 辞書にない英数字トークンで、skill context内に出現するもの
- confidence: low
- dry-run report に "候補" として記録

**Output:**
```python
@dataclass
class SkillResult:
    skills: list[str]  # 正規化済みスキル名
    raw_skills: list[str]  # 抽出そのままの文字列
    confidence: float
    source: str  # "labeled" | "subject" | "dictionary" | "heuristic"
```

### 5.2 Rate Extractor (Engineer)
**Target patterns:**
- `【7月〜65万（応相談）】` → 65
- `【単価】40万円(応相談)` → 40
- `単価: 65万` → 65
- `60〜70万` → {"min": 60, "max": 70}
- `MAX65万` → 65
- `65万前後` → 65
- `スキル見合い` → None (flag: skill_dependent)

**Output:**
```python
@dataclass
class RateResult:
    rate: int | None  # 代表値（万円）
    rate_min: int | None
    rate_max: int | None
    rate_text_raw: str | None
    negotiable: bool  # 応相談フラグ
    skill_dependent: bool
    confidence: float
```

**Notion反映ルール:**
- 単値 → そのまま
- レンジ → max値を使用（SES業界慣行：提案単価はmax基準）
- スキル見合い → 反映しない（shadow reportのみ）

### 5.3 Station Extractor
**Target patterns:**
- `【最寄】船橋競馬場駅` → "船橋競馬場駅"
- `最寄駅：JR埼京線大宮駅` → "大宮駅"
- `最寄り駅：半蔵門線 錦糸町駅` → "錦糸町駅"
- 件名内: `D.E｜蕨駅｜...` → "蕨駅"

**Extraction priority:**
1. labeled_fields（【最寄】等）
2. body内の明示記載
3. subject内の駅名

**Output:**
```python
@dataclass
class StationResult:
    station: str | None  # 駅名
    line: str | None  # 路線名（あれば）
    area: str | None  # 都道府県/エリア
    confidence: float
```

### 5.4 Experience Extractor
**Target patterns:**
- `iOS開発11年` → 11
- `SE経験10年以上` → 10
- `業界歴10年以上` → 10
- `開発経験3.5年` → 3.5
- `4.5年` (in context) → 4.5

### 5.5 Availability Extractor
**Target patterns:**
- `7月〜` → 2026-07-01 (年は受信日基準で補完)
- `7月以降稼働可` → 2026-07-01
- `即日` / `即` → today
- `2026/07/01～` → 2026-07-01
- `【開始】7月～` → 2026-07-01

### 5.6 Demographics Extractor
**Target patterns:**
- `33歳/男性` → age=33, gender="男性"
- `40歳女性` → age=40, gender="女性"
- `(32)男性` → age=32, gender="男性"
- `27歳` → age=27

## 6. Merge Policy
### 6.1 Core Rule
**fill empty, never overwrite**

### 6.2 Field-specific rules
| Field | Empty definition | Update target |
|-------|-----------------|---------------|
| スキル | multi_select empty | append extracted skills |
| 単価（万円）| None or 0 | set rate |
| 最寄り駅 | empty string | set station |
| 経験年数 | None | set years |
| 稼働可能日 | None | set date |
| 居住地 | None (select) | set if area detected |

### 6.3 Conflict reporting
既存値あり + 新抽出値あり → shadow report に記録:
- record_id, field, existing_value, extracted_value, source_snippet, confidence

## 7. Execution Modes
### --dry-run (default)
- Notion更新なし
- コンソール + JSONレポート出力

### --shadow-write
- Notion更新なし
- ローカルに shadow_report.json 出力

### --apply
- merge policy通過の空欄のみNotionを更新
- 更新ログを update_log.json に保存
- rollback用の pre_update_snapshot.json を事前保存

## 8. Reports
### Summary Report
- 処理件数
- パターン別件数
- フィールド別: 抽出成功/更新対象/conflict/error
- 改善率（before/after）

### Detailed Report (JSON)
```json
{
  "records": [
    {
      "id": "page_id",
      "name": "Y.S",
      "pattern": "line_register",
      "extracted": {
        "skills": {"value": ["PHP", "Java"], "confidence": 0.95, "source": "labeled"},
        "rate": {"value": 40, "confidence": 0.9, "source": "labeled"}
      },
      "updates": {"最寄り駅": {"old": null, "new": "船橋競馬場駅"}},
      "conflicts": {},
      "errors": []
    }
  ]
}
```

## 9. Skill Dictionary (初期版)
skill_dictionary.json に以下カテゴリで200+語を定義:

**Languages:** Python, Java, JavaScript, TypeScript, PHP, Ruby, C#, C++, C, Go, Rust, Kotlin, Swift, Scala, Perl, VB, VB.NET, VBA, COBOL, R, Dart, Objective-C, Shell, Bash, PowerShell

**Frameworks:** React, Vue, Angular, Next.js, Nuxt, Node.js, Express, Django, Flask, FastAPI, Spring, Spring Boot, Laravel, Rails, Ruby on Rails, .NET, ASP.NET, Struts, Hibernate, jQuery, Bootstrap, Tailwind

**Cloud:** AWS, Azure, GCP, OCI, Alibaba Cloud, EC2, S3, Lambda, VPC, RDS, ECS, EKS, Fargate, CloudFormation, CDK, Terraform, Ansible, Kubernetes, Docker, Podman

**DB:** MySQL, PostgreSQL, Oracle, SQL Server, SQLite, MongoDB, Redis, DynamoDB, Cassandra, Elasticsearch, BigQuery, Redshift, Snowflake

**Middleware/Tools:** Apache, Nginx, Tomcat, IIS, JP1, Zabbix, Datadog, Prometheus, Grafana, Jenkins, CircleCI, GitHub Actions, GitLab CI, Ansible, Chef, Puppet, CLUSTERPRO, HAProxy, Pacemaker, ServiceNow

**OS:** Linux, Windows, Windows Server, RHEL, CentOS, Ubuntu, Amazon Linux, macOS, Unix, AIX, Solaris

**Infra:** VMware, Hyper-V, Citrix, Active Directory, LDAP, DNS, DHCP, TCP/IP, VPN, Firewall, Load Balancer, CDN, WAF, SSL/TLS

**Data/AI:** Pandas, NumPy, Scikit-learn, TensorFlow, PyTorch, Jupyter, Spark, Hadoop, Kafka, Airflow, dbt, Tableau, Power BI, Looker

**Testing:** JUnit, pytest, Selenium, Cypress, Playwright, JSTQB, TestRail, Postman

**PM/Other:** Jira, Confluence, Backlog, Redmine, Notion, Slack, Teams, Git, GitHub, GitLab, SVN, Agile, Scrum, SAP, Salesforce, kintone, M365, SharePoint

## 10. Rollback
1. apply前に pre_update_snapshot.json を保存
2. update_log.json に全変更を記録
3. rollback_runner.py で直近のapplyを差し戻し可能
4. Notion APIのPATCHでフィールド単位で元に戻す

## 11. Dependencies
- Python 3.10+
- requests (Notion API)
- pytest (testing)
- 既存 config/.env (NOTION_API_KEY)
- LLMは使わない（Phase 1はルールベースのみ）

## 12. Success Criteria
- スキル空欄: 35件 → 10件以下
- 単価空欄: 35件 → 10件以下
- 最寄り駅: 4件 → 80件以上
- 誤更新: 0件
- dry-run 30件レビューで精度80%以上
