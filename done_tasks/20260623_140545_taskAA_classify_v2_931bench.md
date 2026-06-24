# 【Cursor作業指示】Task AA: 分類精度本格改善（931件ベンチマーク+GPT-5.4分析）

対象ファイル: ses_work/analyze_final.py
作業内容: 分類ロジック再設計（5項目の構造的改善）
参照ファイル: CLAUDE.md / research_results/GPT_CLASSIFY_931_20260623.md
完了条件: 931件ベンチマーク再実行で下記目標達成
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 現状（931件ベンチマーク, seed=42）
| 指標 | 現状 | 目標 |
|---|---|---|
| project→engineer混入 | 49/400 (12.2%) | ≤21/400 (5%) |
| skip→project損失 | 20/250 (8.0%) | ≤6/250 (2.4%) |
| project→unknown | 23/400 (5.8%) | ≤12/400 (3%) |
| project→other | 2/400 (0.5%) | 維持 |

---

## 改善1: skip先行確定の廃止 → フラグ化

```python
# 変更前: skipで即return
for pat in SKIP_PATTERNS:
    if re.search(pat, subj + " " + frm):
        return "skip"

# 変更後: フラグだけ立てて、最終判定で使う
skip_hit = False
for pat in SKIP_PATTERNS:
    if re.search(pat, subj + " " + frm):
        skip_hit = True
        break

# 最終判定時:
# strong_proj が True → skip無視してproject
# それ以外で skip_hit → skip
```

skip→project 20件中14件を回収する。「案件一覧」「急募案件」「7月案件」等がskipに落ちなくなる。
弊社プロパー+案件語の場合（人材が案件を探している）は rescue を抑制する。

## 改善2: engineer確定条件の厳格化

```python
# 変更前:
if eng_score >= 3 and eng_score >= proj_score:
    return "engineer"

# 変更後:
if eng_score >= 4 and eng_score >= proj_score + 2 and not strong_proj:
    return "engineer"
```

ENGINEER_PATTERNSから以下を**単独加点対象から除外**（複合条件へ移動）:
- `希望` → 「案件希望」は人材、「スキル希望」は案件。単独では判定不能
- `PMO`, `社内SE`, `SE`, `PG` → role名だけでは人材/案件の区別不能
- 「常駐可」→ 案件側にもある

これらは年齢/性別/所属/稼働可 等のhuman明示語と**組み合わせ**でのみeng加点:
```python
# 複合条件: role名 + human明示語 → eng+3
r"(?:PM補佐|PMO|社内SE|フロントエンジニア)(?=.*(歳|男性|女性|正社員|弊社|プロパー|要員|稼働可能))"
```

project→engineer 49件中12件を解消。

## 改善3: STRONG_PROJECT / STRONG_ENGINEER の新設

```python
STRONG_PROJECT_PATTERNS = [
    r"案件.*(?:Java|PHP|Python|Ruby|COBOL|AWS|Azure|NW|C#|Go|TypeScript|SAP)",
    r"案件.*(?:\d{2,3})万",
    r"案件.*(?:基本設計|詳細設計|保守|運用|テスト)",
    r"(?:向けシステム|向け開発|統合案件|開発案件|注力案件)",
    r"案件概要|業務内容|担当工程|募集人数|スキル要件",
]

STRONG_ENGINEER_PATTERNS = [
    r"直個人|直フリーランス|弊社フリーランス",
    r"(?:\d{2})歳\s*[／/]\s*(?:男性|女性)",
    r"おすすめ人材|注力人材|弊社プロパー.*紹介",
    r"要員配信|人材配信",
    r"スキルシート.*添付|経歴書.*送付",
]
```

判定順を変更:
```
strong_proj > strong_eng > score判定 > skip_hit > other > unknown
```

project→engineer 49件中16件を解消。

## 改善4: 曖昧語の複合条件化

以下のパターンは**単独では無加点**、human/project語との複合でのみ加点:
```python
AMBIGUOUS_ENGINEER = [
    # (trigger, require_context) の組
    (r"希望", r"(?:案件.*探し|単価|勤務地|稼働|参画)"),
    (r"(?:PM補佐|PMO|SE|PG)", r"(?:\d+歳|男性|女性|正社員|プロパー|要員)"),
    (r"常駐可", r"(?:弊社|当社|所属|要員)"),
]
```

## 改善5: 本文テンプレ語による救済（件名曖昧時）

```python
# 案件テンプレ語（2個以上ヒットでproj+3）
BODY_PROJECT_TEMPLATE = [
    r"案件概要", r"勤務場所|作業場所", r"期間[:：]",
    r"単価[:：]", r"面談[:：]|面談\d+回", r"募集人数",
    r"スキル要件|必須スキル|尚可スキル",
]

# 人材テンプレ語（2個以上ヒットでeng+3）
BODY_ENGINEER_TEMPLATE = [
    r"(?:氏名|名前)\s*[:：]", r"(?:年齢|性別)\s*[:：]",
    r"(?:所属|最寄)\s*[:：]", r"(?:希望単価|単金)\s*[:：]",
    r"(?:並行|稼働率)\s*[:：]", r"(?:保有スキル|経験年数)\s*[:：]",
]
```

project→unknown 23件中11件を回収。

## テスト要件

### 1. 既存テスト
`mail_pipeline/tests/test_task_y_classify.py` が全PASS

### 2. 931件ベンチマーク（メインテスト）
`mail_pipeline/tests/test_benchmark_931.py` を新規作成:

```python
import sqlite3, random
from analyze_final import classify_by_rule

def test_benchmark():
    # raw_inbox.dbから同一seed=42でサンプリング
    # project:400, skip:250, other:250, engineer:31
    
    # Assert targets:
    assert project_to_engineer <= 21, f"project→engineer {project_to_engineer}/400 exceeds 21"
    assert skip_to_project <= 6, f"skip→project {skip_to_project}/250 exceeds 6"
    assert project_to_unknown <= 12, f"project→unknown {project_to_unknown}/400 exceeds 12"
```

### 3. 加点ログ出力
テスト実行時に各サンプルの**加点理由ログ**を出力:
```
[project→engineer] 件名: XXX | eng_hits: [弊社プロパー(+3), 50歳(+2)] | proj_hits: [案件(+2)] | verdict: engineer
```

これにより次の改善サイクルで過剰加点語を特定できる。

## 禁止事項
- project維持率（326/400=82%）を75%未満に下げない
- engineer検出率（31/31=100%）を下げない
- LLMコールを追加しない
- 改善前のスコアリング結果をログに保存して回帰比較可能にする
