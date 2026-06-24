# 【Cursor作業指示】Task Q: 案件情報抽出精度改善（単価+スキル）

対象ディレクトリ: ses_work/mail_pipeline/
作業内容: AI-first抽出をRule-first+AI-fallbackに改修
参照ファイル: CLAUDE.md / research_results/GPT_WALLHIT_DB_QUALITY_20260622.md
完了条件: No skills 56%→35%以下、No price 48%→25%以下、price anomaly 0件
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 背景
Notion案件DBの56%がスキル未設定、48%が単価未設定。AI抽出(gpt-4.1-nano)が日本語SESメールの構造化フォーマットを正しくパースできていない。

## 修正1: 単価抽出のRule-first化

### 新規ファイル: mail_pipeline/price_extractor.py

```python
import re, unicodedata

def extract_price(subject: str, body: str) -> dict:
    # Returns: {value: float|None, unit: 'monthly'|'annual'|'daily'|None, raw: str, confidence: str}
    
    # Step 1: Subject regex
    result = _extract_from_text(subject)
    if result["value"]: return result
    
    # Step 2: Body regex (first 500 chars around price keywords)
    result = _extract_from_text(body[:1500])
    if result["value"]: return result
    
    return {"value": None, "unit": None, "raw": "", "confidence": "none"}

def _extract_from_text(text: str) -> dict:
    text = unicodedata.normalize("NFKC", text)
    
    # Range pattern: 80〜100万 → take lower bound
    m = re.search(r'(\d{2,3})\s*[〜~～\-]\s*(\d{2,3})\s*万', text)
    if m:
        lower = float(m.group(1))
        return _classify(lower, text, m.group(0))
    
    # MAX pattern: MAX90万 → take value
    m = re.search(r'[Mm][Aa][Xx]\s*(\d{2,3})\s*万', text)
    if m:
        return _classify(float(m.group(1)), text, m.group(0))
    
    # 〜N万 pattern: 〜65万 → take value
    m = re.search(r'[〜~～]\s*(\d{2,3})\s*万', text)
    if m:
        return _classify(float(m.group(1)), text, m.group(0))
    
    # 単価:N / 月額:N pattern
    m = re.search(r'(?:単価|月額|予算|単金)[：:\s]*(\d{2,3})', text)
    if m:
        return _classify(float(m.group(1)), text, m.group(0))
    
    # Standalone N万 / N万円 (2-3 digits + 万)
    m = re.search(r'(\d{2,3})\s*万(?:円)?', text)
    if m:
        return _classify(float(m.group(1)), text, m.group(0))
    
    return {"value": None, "unit": None, "raw": "", "confidence": "none"}

def _classify(value: float, context: str, raw: str) -> dict:
    # Detect annual salary
    if re.search(r'年収|賞与|昇給|想定年収', context):
        return {"value": value, "unit": "annual", "raw": raw, "confidence": "high",
                "normalized_monthly": round(value / 12, 1)}
    
    # Detect daily rate
    if re.search(r'/日|日額|人日|日当', context):
        return {"value": value, "unit": "daily", "raw": raw, "confidence": "high",
                "normalized_monthly": round(value * 20, 1)}
    
    # Monthly (default for SES)
    confidence = "high"
    if value > 200:
        confidence = "suspicious"  # Likely annual or error
    elif value < 15:
        confidence = "suspicious"  # Likely daily or error
    
    return {"value": value, "unit": "monthly", "raw": raw, "confidence": confidence}
```

### mail_pipeline.pyへの統合
register_projectの単価設定箇所に追加:
```python
from mail_pipeline.price_extractor import extract_price

# AI抽出結果の単価
ai_price = info.get("price")

# Rule-based抽出（AI結果がない or 異常値の場合のfallback）
rule_result = extract_price(subject, body)
if rule_result["confidence"] == "high" and rule_result["unit"] == "monthly":
    final_price = rule_result["value"]
elif ai_price and 15 <= ai_price <= 200:
    final_price = ai_price
elif rule_result["value"] and rule_result["confidence"] != "suspicious":
    final_price = rule_result["value"]
else:
    final_price = None  # 不明
```

---

## 修正2: スキル抽出のRule-first化

### 新規ファイル: mail_pipeline/skill_extractor.py

```python
import re, unicodedata

KNOWN_SKILLS = {
    # Languages
    "java", "python", "go", "php", "ruby", "c#", "kotlin", "scala",
    "javascript", "typescript", "swift", "objective-c", "dart", "rust",
    "vb.net", "vba", "cobol", "pl/sql", "pl/i", "c++", "c言語", "perl",
    # Frameworks
    "spring", "spring boot", "django", "laravel", "rails", "flask",
    "react", "vue", "angular", "next.js", "nuxt", "node.js", "express",
    "flutter", "mybatis", "struts", "hibernate",
    # DB
    "oracle", "mysql", "postgresql", "sql server", "redis", "dynamodb",
    "mongodb", "aurora", "sql",
    # Cloud
    "aws", "azure", "gcp", "google cloud",
    # Infra
    "docker", "kubernetes", "terraform", "ansible", "linux", "windows server",
    "vmware", "cisco", "jp1", "zabbix", "nagios",
    # Tools
    "git", "jenkins", "jira", "confluence",
    # Roles
    "pmo", "pm", "pl", "se", "sre", "dba",
    # ERP
    "sap", "salesforce", "servicenow", "dynamics", "grandit",
    # Other
    "uipath", "power bi", "tableau", "excel", "rpa",
}

HEADER_PATTERNS = [
    r'(?:必要|必須)(?:スキル)?[：:\s]*(.*?)(?:
|$)',
    r'■必須[：:\s]*(.*?)(?:
|$)',
    r'【必要スキル】(.*?)(?:
|$)',
    r'【必須】(.*?)(?:
|$)',
    r'(?:尚可|歓迎)(?:スキル)?[：:\s]*(.*?)(?:
|$)',
    r'【尚可】(.*?)(?:
|$)',
]

def extract_skills(subject: str, body: str) -> dict:
    # Returns: {required: list, optional: list, source: str}
    required = set()
    optional = set()
    
    text = unicodedata.normalize("NFKC", subject + " " + (body or "")[:2000])
    
    # Step 1: Header-based extraction from body
    for pat in HEADER_PATTERNS:
        for m in re.finditer(pat, text, re.IGNORECASE):
            skills_text = m.group(1)
            found = _split_skills(skills_text)
            if '必須' in pat or '必要' in pat:
                required.update(found)
            else:
                optional.update(found)
    
    # Step 2: Known-skill dictionary scan (if header extraction found nothing)
    if not required and not optional:
        text_lower = text.lower()
        for skill in KNOWN_SKILLS:
            if skill in text_lower:
                required.add(skill)
    
    return {"required": sorted(required), "optional": sorted(optional),
            "source": "header" if required or optional else "dictionary"}

def _split_skills(text: str) -> set:
    # Split skill text by common delimiters
    parts = re.split(r'[,、/|・
　]', text)
    result = set()
    for part in parts:
        part = part.strip()
        if not part: continue
        # Remove experience suffixes
        part = re.sub(r'[(（][^)）]*[)）]', '', part).strip()
        part = re.sub(r'\d+年以上', '', part).strip()
        if part and len(part) >= 1:
            result.add(part.lower())
    return result
```

### mail_pipeline.pyへの統合
register_projectのスキル設定箇所に追加:
```python
from mail_pipeline.skill_extractor import extract_skills

# AI抽出結果
ai_skills = info.get("required_skills", [])
ai_optional = info.get("optional_skills", [])

# Rule-based抽出
rule_result = extract_skills(subject, body)

# マージ（AI + Rule、重複排除）
final_required = list(set(ai_skills + rule_result["required"]))
final_optional = list(set(ai_optional + rule_result["optional"]))
```

---

## テスト要件

### テスト1: price_extractor
- "PMO案件/〜65万/損保" → 65, monthly, high
- "80〜100万" → 80, monthly, high
- "想定年収625万" → 625, annual, high, normalized_monthly=52.1
- "1.5万/日" → 1.5, daily, high, normalized_monthly=30
- "MAX90万" → 90, monthly, high
- "875万" (no context) → 875, monthly, suspicious

### テスト2: skill_extractor
- "【必要スキル】Java, Spring Boot, Oracle" → required=[java, spring boot, oracle]
- "■必須：Java（3年以上）、SQL" → required=[java, sql]
- "React/Vue/TypeScript フロント開発" → required=[react, vue, typescript] (dictionary)
- "PMO案件/〜65万" → required=[pmo] (dictionary)

### テスト3: 統合テスト
- 50件のproject emailsに適用し、price recovery率とskill recovery率を計測
- 目標: No skills 56%→35%以下、No price 48%→25%以下

---

## 禁止事項
- 既存のAI抽出ロジック(classify_email)を削除しない（fallbackとして維持）
- CostGuardを迂回しない
- Notion DBスキーマを変更しない（既存プロパティに書き込む）


## RETRY 1 REASON
exit=1 / stderr=�R�}���h ���C�����������܂��B




## RETRY 2 REASON
exit=1 / stderr=�R�}���h ���C�����������܂��B



## BLOCKED REASON
exit=1 / stderr=コマンド ラインが長すぎます。

---

## 完了メモ（2026-06-22）

- `mail_pipeline/price_extractor.py` / `skill_extractor.py` 新規
- `register_project()` に Rule-first + AI-fallback 統合
- テスト 15 passed (`test_task_q_extraction.py`)
- 回収率: 50件 skills 24% no-skill ✓ / price 56% no-price
- 500件: skills 25.8% / price 32.2%
