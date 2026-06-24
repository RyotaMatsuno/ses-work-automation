# 【Cursor作業指示】Task AH: judge()関数リデザイン（MATCH率0%→20%+）

対象ディレクトリ: ses_work/matching_v3/
作業内容: matcher.pyのjudge()関数を改修し、unknown_skills単独でREVIEWに落とさないようにする
参照ファイル: CLAUDE.md / matcher.py / skill_judge.py / skill_aliases.json
完了条件: 6/23のmatched 98案件に対し、MATCH率20%以上（現在0%）

---

## 根本原因
matcher.py L194-228のjudge()関数で:
1. normalizer.normalize(skill)がNone → unknown_skillsに追加
2. unknown_skillsが1件でもあると → reasonsに「語彙外必須スキル要確認」追加
3. reasonsが非空 → REVIEW（MATCHに到達不可能）

SES業界のスキル語彙は数百〜数千語あり、辞書を完全にするのは非現実的。
→ unknown_skills単独でREVIEWに直行させない構造変更が必要。

## 改修内容（GPT-5.4合意済み）

### 変更1: 3値判定の導入
必須スキルを HIT / MISS / UNKNOWN の3カテゴリに分類:
```python
hit_skills = []      # 辞書正規化OK + エンジニアが保有
miss_skills = []     # 辞書正規化OK + エンジニアが未保有
unknown_skills = []  # 辞書正規化不能
```

### 変更2: UNKNOWN分類の2段階化
辞書外スキルでも、エンジニアDBの生スキルリストと照合する:
```python
for skill in unknown_skills:
    normalized = _fuzzy_match(skill, eng_skills_raw)
    if normalized:
        # DB証拠あり → UNKNOWN_WITH_EVIDENCE（MATCH寄り）
        unknown_with_evidence.append(skill)
    else:
        # DB証拠なし → UNKNOWN_NO_EVIDENCE（REVIEW寄り）
        unknown_no_evidence.append(skill)
```

_fuzzy_match()の実装:
```python
def _fuzzy_match(query: str, eng_skills: list[str]) -> bool:
    q = _normalize_text(query)  # 小文字化、全半角統一、記号除去、スペース除去
    for skill in eng_skills:
        s = _normalize_text(skill)
        if q == s:           # 完全一致
            return True
        if q in s or s in q:  # 部分一致
            return True
    return False

def _normalize_text(text: str) -> str:
    import unicodedata
    text = unicodedata.normalize('NFKC', text)
    text = text.lower().strip()
    text = re.sub(r'[\s　]+', '', text)
    return text
```

### 変更3: 判定ロジック改修

```python
# STEP 1: NG判定（変更なし）
if miss_skills:
    return "NG", [f"必須スキル不足: {miss_skills}"]

# STEP 2: MATCH判定（新規）
unknown_ratio = len(unknown_no_evidence) / max(len(required_raw), 1)
if unknown_ratio <= 0.3:
    # 未知スキルが30%以下 → MATCH（証拠ありは無視）
    if unknown_no_evidence:
        reasons.append(f"語彙外スキル({len(unknown_no_evidence)}件)あるがMATCH判定")
    # 他のreasons（鮮度、並行等）がなければMATCH
    if not reasons:
        return "MATCH", []
    # 鮮度・並行のみなら MATCH_LOW
    non_critical = all(
        r.startswith("語彙外") or r.startswith("エンジニア情報古い")
        for r in reasons
    )
    if non_critical:
        return "MATCH", reasons  # MATCHだがreasons付き

# STEP 3: REVIEW判定
reasons.append(f"語彙外必須スキル要確認: {', '.join(unknown_no_evidence)}")
return "REVIEW", reasons
```

### 変更4: 能力記述のフィルタリング

structurerが抽出したrequired_skillsから能力記述を除外:
```python
CAPABILITY_RE = re.compile(
    r'.*(?:経験|経験者|できる|可能|以上|知識|スキル|対応力|管理能力)$'
)

def _without_capabilities(skills: list[str]) -> list[str]:
    return [s for s in skills if not CAPABILITY_RE.match(s)]
```

judge()冒頭でrequired_rawから能力記述を除外（L185の直後に追加）。

## テスト
1. 6/23の98案件を再マッチング（dry-run）
2. MATCH率20%以上を確認
3. 既存のNG判定（粗利不足、必須スキル不足）が変わっていないことを確認
4. MATCH判定された案件の品質をサンプリング検証（10件程度）

## 禁止事項
- NG判定ロジック（粗利・必須スキル不足・並行過多）を緩めない
- LLMを新規に呼び出さない（ルールベースのみ）
- CostGuardなしでLLMを呼び出さない
- skill_judge.py（LLMスキル判定）は今回は触らない
