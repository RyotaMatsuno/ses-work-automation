# 【Cursor作業指示】Task P: マッチング精度改善（Cloud Run webhook_server.py）

対象ディレクトリ: ses_work/line_webhook/
作業内容: run_reverse_matchingの除外ロジック修正 + スキル正規化
完了条件: gross>15除外撤廃 + スキル正規化 + 除外理由ログ追加 + テスト
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 背景
「PH 京成小岩」等のLINE経由マッチングで「マッチ案件なし」が返る。
案件DBには179件の募集中案件があるのに0件マッチ。
原因: (1) gross>15除外が厳しすぎる (2) スキル完全一致が表記ゆれに対応できない

## 修正1: run_reverse_matching の粗利フィルタ緩和

### 対象ファイル
line_webhook/webhook_server.py L492-535

### 変更前
```python
if eng_price > 0 and proj_price > 0:
    if gross < 0:
        continue
    if gross > 15:
        continue  # ← これが大量除外の原因
```

### 変更後
```python
if eng_price > 0 and proj_price > 0:
    if gross < 0:
        continue  # 粗利マイナスのみ除外
    # gross > 15 は除外しない。スコア調整のみ
```

### スコア調整
```python
# 変更前
gross_pts = min(30, int(30 * gross / 7)) if gross >= 5 else (15 if gross == 0 else 0)

# 変更後
if gross is None or gross == 0:
    gross_pts = 15  # 価格不明/同額: ニュートラル
elif gross >= 5 and gross <= 15:
    gross_pts = min(30, int(30 * gross / 7))  # 理想帯: 加点
elif gross > 15:
    gross_pts = 10  # 高粗利: 軽い加点（除外しない）
else:
    gross_pts = 0  # 粗利5万未満: 加点なし
```

---

## 修正2: スキル正規化

### 新規関数追加（webhook_server.py内、run_reverse_matchingの前）

```python
import unicodedata
import re

SKILL_ALIASES = {
    "aws": {"amazon web services", "aws"},
    "react": {"react.js", "reactjs", "react"},
    "vue": {"vue.js", "vuejs", "vue"},
    "c#": {"csharp", "c#"},
    "javascript": {"js", "javascript"},
    "typescript": {"ts", "typescript"},
    "spring boot": {"springboot", "spring boot", "spring-boot"},
    "spring": {"spring framework", "spring"},
    "next.js": {"nextjs", "next.js", "next"},
    "node.js": {"nodejs", "node.js", "node"},
    ".net": {"dotnet", ".net", "dot net"},
    "python": {"python3", "python"},
    "gcp": {"google cloud platform", "google cloud", "gcp"},
    "azure": {"microsoft azure", "azure"},
}

def _normalize_skill(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s).lower().strip()
    s = s.replace("　", " ")
    s = re.sub(r"\s+", " ", s)
    return s

def _skill_match(required_skill, engineer_skills_normalized):
    req = _normalize_skill(required_skill)
    if not req:
        return False
    # 1. exact match
    if req in engineer_skills_normalized:
        return True
    # 2. alias match
    for canonical, aliases in SKILL_ALIASES.items():
        if req == canonical or req in aliases:
            for alias in aliases | {canonical}:
                if alias in engineer_skills_normalized:
                    return True
    # 3. contains match (only for skills >= 3 chars to avoid false positives)
    if len(req) >= 3:
        for eng_s in engineer_skills_normalized:
            if req in eng_s or eng_s in req:
                return True
    return False
```

### run_reverse_matching内の変更

```python
# 変更前
req_match = {s: (s in eng_skills) for s in req_skills}

# 変更後
eng_skills_normalized = {_normalize_skill(s) for s in eng_skills}
req_match = {s: _skill_match(s, eng_skills_normalized) for s in req_skills}
```

---

## 修正3: 除外理由ログ追加

run_reverse_matchingの戻り値にstatsを追加:

```python
stats = {
    "total_projects": len(projects),
    "excluded_negative_margin": 0,
    "excluded_no_skill_match": 0,
    "passed": 0,
}

for proj in projects:
    ...
    if gross < 0:
        stats["excluded_negative_margin"] += 1
        continue
    if req_skills and not any(req_match.values()):
        stats["excluded_no_skill_match"] += 1
        continue
    stats["passed"] += 1
    matches.append(...)

return {"matches": sorted(...), "stats": stats}
```

build_reverse_match_message_v2にもstatsを渡して、0件時のメッセージにstatsを含める:
```python
if not raw_matches:
    s = stats or {}
    return (
        f"[registered] {eng_name}\n\n"
        f"マッチ案件なし\n"
        f"(対象{s.get('total_projects',0)}件: "
        f"粗利NG {s.get('excluded_negative_margin',0)}件 / "
        f"スキル不一致 {s.get('excluded_no_skill_match',0)}件)"
    )
```

---

## 修正4: matching_logic.py の同期修正

matching_logic.pyのcategorize_matchにも同様のスキル正規化を適用:
- _normalize_skill と _skill_match を共通化
- line_webhook/skill_utils.py に切り出すのが理想的

---

## テスト要件

### テスト1: 粗利フィルタ
- eng_price=60, proj_price=100 (gross=40) → 除外されない（変更前は除外）
- eng_price=60, proj_price=50 (gross=-10) → 除外される
- eng_price=60, proj_price=65 (gross=5) → 通過

### テスト2: スキル正規化
- required="Java", engineer_skills=["java"] → match
- required="React", engineer_skills=["React.js"] → match
- required="AWS", engineer_skills=["Amazon Web Services"] → match
- required="Go", engineer_skills=["Django"] → NO match (短いスキル名)

### テスト3: stats
- 10 projects, 3 negative margin, 5 no skill, 2 passed → stats正確

---

## 禁止事項
- build_reverse_match_message_v2の候補表示フォーマットを変更しない
- Notion DB操作を変更しない
- matching_v3本体のロジックは変更しない（このタスクはwebhook_server.pyのみ）
- Cloud Runデプロイは含めない（松野が手動で行う）

## 実装順序
1. skill_utils.py 作成（_normalize_skill, _skill_match, SKILL_ALIASES）
2. webhook_server.py の run_reverse_matching 修正
3. stats追加 + メッセージ改善
4. matching_logic.py にskill_utils適用
5. テスト作成・実行
