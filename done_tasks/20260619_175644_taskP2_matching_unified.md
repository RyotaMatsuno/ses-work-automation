# 【Cursor作業指示】Task P2: マッチング精度改善（line_query.py + webhook_server.py統合）

対象ディレクトリ: ses_work/line_webhook/ および ses_work/line_query/
作業内容: マッチング0件問題の根本修正 + 共通スキルモジュール化
完了条件: PHさん(37万)でマッチ>0件 + テスト通過
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 背景
「PH 京成小岩」のLINE照会で「マッチ案件なし」が返る。
原因: line_query/line_query.pyに独立したマッチングロジックがあり:
1. 必須スキル空案件を全除外 (案件DBの58%が消える)
2. gross > 15で除外 (PH 37万→70万案件=gross33→除外)
3. #skill_skip未対応
4. スキル完全一致のみ (表記ゆれに弱い)

## 修正1: 共通スキルモジュール作成

### 新規ファイル: line_webhook/skill_utils.py

```python
import unicodedata
import re

SKILL_ALIASES = {
    "aws": {"amazon web services"},
    "react": {"react.js", "reactjs"},
    "vue": {"vue.js", "vuejs"},
    "c#": {"csharp"},
    "javascript": {"js"},
    "typescript": {"ts"},
    "spring boot": {"springboot", "spring-boot"},
    "spring": {"spring framework"},
    "next.js": {"nextjs", "next"},
    "node.js": {"nodejs", "node"},
    ".net": {"dotnet", "dot net"},
    "python": {"python3"},
    "gcp": {"google cloud platform", "google cloud"},
    "azure": {"microsoft azure"},
    "pmo": {"プロジェクトマネジメント"},
    "php": set(),
    "mysql": set(),
    "laravel": set(),
}

def normalize_skill(s):
    if not s: return ""
    s = unicodedata.normalize("NFKC", s).lower().strip()
    s = s.replace("\u3000", " ")
    s = re.sub(r"\s+", " ", s)
    return s

def skill_match(required_skill, engineer_skills_normalized):
    req = normalize_skill(required_skill)
    if not req: return False
    if req in engineer_skills_normalized: return True
    for canonical, aliases in SKILL_ALIASES.items():
        if req == canonical or req in aliases:
            for alias in aliases | {canonical}:
                if alias in engineer_skills_normalized:
                    return True
    if len(req) >= 3:
        for eng_s in engineer_skills_normalized:
            if req in eng_s or eng_s in req:
                return True
    return False

def normalize_skill_set(skills):
    return {normalize_skill(s) for s in skills if s}

def has_skill_skip(note):
    return "#skill_skip" in (note or "")
```

## 修正2: line_query/line_query.py 修正（最重要）

### 修正箇所A: 必須スキル空案件の除外撤廃

変更前 (L340付近):
```python
if not required:
    continue
```

変更後:
```python
# 必須スキル未設定案件も候補に含める
# スキルマッチは設定がある場合のみ判定
```

### 修正箇所B: gross > 15除外の撤廃

変更前 (L347-348付近):
```python
if gross > 15:
    continue
```

変更後: この行を削除またはコメントアウト。粗利は除外条件ではなくスコア調整のみに使用。

### 修正箇所C: #skill_skip対応

エンジニアの備考（Notionプロパティ「備考（LINEメモ）」）から#skill_skipフラグを読み取り、
スキルフィルタを完全スキップする。

```python
from skill_utils import has_skill_skip, normalize_skill_set, skill_match as shared_skill_match

# エンジニア取得後
note = _rich_text_prop(eng, "備考（LINEメモ）")
is_skill_skip = has_skill_skip(note)

# マッチング内
if is_skill_skip:
    pass  # スキルフィルタ不要
elif required:
    eng_skills_norm = normalize_skill_set(eng_skills)
    if not any(shared_skill_match(r, eng_skills_norm) for r in required):
        continue
```

### 修正箇所D: スキルマッチ関数をskill_utils版に差し替え

既存のskill_match関数をskill_utils.skill_matchに置き換え。

### 修正箇所E: L376-378も同様に修正（逆引きの方向）

L376-378にもgross > 15があるので同様に撤廃。

## 修正3: webhook_server.py run_reverse_matching修正

### 修正箇所A: gross > 15除外撤廃

変更前 (L510-511):
```python
if not skill_skip and gross > 15:
    continue
```

変更後: この行を削除。

### 修正箇所B: #skill_skip時のgross > 10も撤廃

変更前 (L508-509):
```python
if skill_skip and gross > 10:
    continue
```

変更後: この行を削除。

### 修正箇所C: スキルマッチをskill_utils版に差し替え

```python
from skill_utils import normalize_skill_set, skill_match as shared_skill_match

eng_skills_normalized = normalize_skill_set(eng_skills)
req_match = {s: shared_skill_match(s, eng_skills_normalized) for s in req_skills}
```

## 修正4: 除外理由ログ（両ファイル共通）

マッチング関数の戻り値にstatsを追加:
```python
stats = {"total": len(projects), "excluded_margin": 0, "excluded_skill": 0, "passed": 0}
```

0件時のLINEメッセージにstatsを含める。

## テスト要件

### テスト1: line_query マッチング
- PH (37万, skills=[PMO,PHP,...], #skill_skip) → マッチ件数 > 0
- 必須スキル空案件 → 除外されない
- gross=33案件 → 除外されない
- gross=-5案件 → 除外される

### テスト2: webhook_server マッチング
- 同上（run_reverse_matchingで同じ結果）

### テスト3: skill_utils
- normalize_skill("Java") == "java"
- skill_match("React", {"react.js"}) == True
- skill_match("Go", {"django"}) == False

## 実装順序
1. line_webhook/skill_utils.py 作成
2. line_query/line_query.py 修正（L340, L347-348, L376-378, #skill_skip, スキル関数差し替え）
3. webhook_server.py 修正（L508-511, スキル関数差し替え）
4. stats + 除外理由ログ
5. テスト作成・実行

## 禁止事項
- Notion DB操作を変更しない
- Cloud Runデプロイは含めない
- matching_v3本体のロジックは変更しない
