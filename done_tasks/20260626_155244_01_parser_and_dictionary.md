# 01_parser_and_dictionary.md
# Engineer Text Parser & Skill Dictionary

## Cursor作業指示
対象ディレクトリ: ses_work/engineer_extractor/
作業内容: テキストパーサーとスキル辞書の作成
参照ファイル: SPEC.md / CLAUDE.md / TASKS.md
完了条件: テスト全パス、3パターンのテキスト解析が動作

## 詳細

### 1. engineer_text_parser.py
3種類のテキストパターンを判定し、subject/body/labeled_fieldsに分離する。

#### Pattern 1: [自動取込]
```
[自動取込] 件名: 【SasaTech 人材】【7月〜65万（応相談）】【RHEL / CLUSTERPRO / JP1】...
送信元: 株式会社SasaTech SES事業部<ses@sasatech.co.jp>
受信日: Wed, 17 Jun 2026 07:03:13 +0900 (JST)
```
- `件名:` の後ろのテキスト → subject
- `送信元:` → sender
- `受信日:` → received_date
- 残り → body

#### Pattern 2: 【メールから自動登録】
```
【メールから自動登録】
送信者: sales@conviction-inc.com
件名: D.E｜蕨駅｜iOS開発11年／Swift・Kotlin・Java...
40歳女性。最寄駅：JR埼京線大宮駅。...
```
- `件名:` の後ろ → subject
- `送信者:` → sender
- 残り → body

#### Pattern 3: [LINE登録/auto-register]
```
[LINE登録: matsuno]
【名前】Y.S（33歳男性）
【単価】40万円(応相談)
【スキル】PHP, Java, SQL...
```
- `【ラベル名】値` を labeled_fields dict に格納
- 全文 → body

#### Output dataclass:
```python
@dataclass
class ParsedEngineerText:
    pattern_type: str  # "auto_import" | "email_register" | "line_register" | "unknown"
    subject: str | None
    body: str
    labeled_fields: dict[str, str]
    sender: str | None
    received_date: str | None
    full_text: str
```

### 2. skill_dictionary.json
SPEC.md の Section 9 を参照。200語以上の技術用語辞書。
構造:
```json
{
  "languages": ["Python", "Java", ...],
  "frameworks": ["React", "Spring Boot", ...],
  "cloud": ["AWS", "Azure", ...],
  "databases": ["MySQL", "PostgreSQL", ...],
  "middleware": ["JP1", "Zabbix", ...],
  "os": ["Linux", "Windows Server", ...],
  "infrastructure": ["Docker", "Kubernetes", ...],
  "data_ai": ["Pandas", "TensorFlow", ...],
  "testing": ["pytest", "Selenium", ...],
  "pm_tools": ["Jira", "Git", ...],
  "aliases": {
    "JS": "JavaScript",
    "TS": "TypeScript",
    "RoR": "Ruby on Rails",
    "GCP": "Google Cloud Platform",
    "k8s": "Kubernetes"
  }
}
```

### 3. tests/test_parser.py
- テストデータ: 上記3パターンの実サンプル
- テスト: pattern判定、subject抽出、labeled_fields抽出
- エッジケース: 空テキスト、両フィールド空、混合パターン

### 4. __init__.py
パッケージ初期化。ParsedEngineerText をエクスポート。

### 5. ディレクトリ構造
```
engineer_extractor/
  __init__.py
  engineer_text_parser.py
  skill_dictionary.json
  field_extractors/
    __init__.py
  tests/
    __init__.py
    test_parser.py
    fixtures/
      sample_texts.py  (テストデータ)
```
