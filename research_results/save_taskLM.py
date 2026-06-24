import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

base = os.path.join(os.environ["USERPROFILE"], "OneDrive", "\u30c7\u30b9\u30af\u30c8\u30c3\u30d7", "ses_work")
pending = os.path.join(base, "pending_tasks")

task_l = r"""# 【Cursor作業指示】Task L: 分類精度改善（other→project漏れ修正）【最優先】

対象ディレクトリ: ses_work/
作業内容: analyze_final.pyのルール分類を強化し、案件メールのother漏れを修正
完了条件: 下記テストケース全パス + 既存テスト全パス
質問がある場合: Claude.aiチャットに貼り付けて確認

**緊急度: 高。141件の案件メールがother判定でNotion未登録になっている。**

---

## 問題の全容

379件がother判定。内訳:
- 件名に「案件」含む: 141件 → 本来project
- 件名に「要員/人材」含む: 132件 → 本来skip
- その他: 106件 → ほぼ全部案件（単価・期間・勤務地表記から明らか）

## 原因

analyze_final.pyのPROJECT_PATTERNSが「【案件】」等の明確なプレフィックスしか拾えない。
SES業界で一般的な以下パターンが未対応:

1. 「案件配信」「案件募集」→ unknownになる
2. 「〜65万円」「60万」等の単価表記 → engineer誤判定（→skip統合）
3. 「7月〜」「8月開始」等の期間表記 → unknown
4. 「募集」「常駐」「リモート」「面談N回」→ unknown
5. 「決済者直」「元請け直」「上位増員枠」→ unknown

## 修正方針

### 1. PROJECT_PATTERNSに追加すべきパターン

```python
# 案件配信・案件募集
r'案件配信|案件募集',
# 単価表記（案件の特徴）
r'[\d０-９]{2,3}\s*[万萬]\s*[円〜～\-]',
r'[〜～]\s*[\d０-９]{2,3}\s*[万萬]',
# 期間表記
r'[67891012]\s*月\s*[〜～開始]',
r'即日\s*[〜～開始]',
# 募集キーワード
r'募集|常駐|増員',
# 面談
r'面談\s*[\d１-３]\s*回',
r'WEB面談|対面面談',
# 商流・契約
r'決済者直|元請[けケ]直|準委任|業務委託',
# 勤務地パターン（駅名・エリア+案件的文脈）
r'(?:フルリモート|リモート[可併])',
```

### 2. engineer誤判定の修正（skip統合問題）

classify_email_v2内で`engineer`判定→`skip`にしているが、
件名に「案件」「募集」「〜万」「常駐」等があればengineerではなくproject。

analyze_final.pyの classify_by_rule() を修正:

```python
def classify_by_rule(subject, sender):
    subj = subject or ""

    # ★ PROJECT優先判定（engineer判定より先に実行）
    # 件名に案件キーワードがあればengineerパターンより優先
    PROJECT_PRIORITY_KEYWORDS = [
        '案件', '募集', '常駐', '増員', '面談',
        '準委任', '業務委託', '決済者直', '元請',
    ]
    has_project_keyword = any(kw in subj for kw in PROJECT_PRIORITY_KEYWORDS)

    # 単価表記チェック（案件の特徴: 「〜65万」「60万〜」）
    import re
    has_price = bool(re.search(r'[\d０-９]{2,3}\s*[万萬]', subj))

    # 期間表記チェック（「7月〜」「即日〜」）
    has_period = bool(re.search(r'[0-9０-９]{1,2}\s*月\s*[〜～開始]|即日\s*[〜～開始]', subj))

    if has_project_keyword or (has_price and has_period):
        # PROJECT_PATTERNSに該当するかチェック
        for pat in PROJECT_PATTERNS:
            if pat.search(subj):
                return "project"
        # パターン非該当でもキーワード2つ以上あればproject
        score = sum([has_project_keyword, has_price, has_period])
        if score >= 2:
            return "project"

    # 既存のルール分類（SKIP → ENGINEER → PROJECT → unknown）
    ...
```

### 3. AI分類のフォールバック改善

classify_email_v2のAI分類プロンプト（classify_system）で
type="other"が返ってきた場合、件名に案件キーワードがあればprojectに再分類:

```python
if mail_type in ("other",):
    # other判定だが件名に案件キーワードがある場合はprojectに昇格
    if has_project_keyword or (has_price and has_period):
        mail_type = "project"
```

## テストケース（必須）

analyze_final.py のテスト:
- 「【案件配信】7月〜/UiPath案件」→ project
- 「【フルリモート/〜65万円/TypeScript】AI開発」→ project（engineerではない）
- 「決済者直【C/C++/常駐】」→ project
- 「【8月開始】購買管理システムPL/SQL募集（4名）」→ project
- 「★フルリモート!【Go / 80万～90万】EC開発」→ project
- 「【SES交流会】つながりが次の案件をつくる」→ skip（セミナー案内）
- 「【イルミナ：要員】M.N（29歳）」→ skip（人員紹介）
- 「【ベテランPM要員】PM,PMO」→ skip（人員紹介）
- 「【BTM案件】Go/基本リモート」→ project（Task A修正済み）
- 「お世話になっております」→ unknown（一般メール）

## other再分類（バックログ処理）

修正後に既存のother判定レコードを再処理する仕組みも必要:
```python
# raw_inbox.py に再分類用関数を追加
def reset_other_for_reclassify(db_path):
    """other判定かつ件名に案件キーワードを含むレコードのprocessed=0にリセット"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
        UPDATE raw_emails SET processed=0, retry_count=0
        WHERE classify_result='other'
        AND (subject LIKE '%案件%' OR subject LIKE '%募集%' OR subject LIKE '%常駐%'
             OR subject LIKE '%万円%' OR subject LIKE '%万〜%' OR subject LIKE '%面談%')
    """)
    count = c.rowcount
    conn.commit()
    conn.close()
    return count
```

---

## 共通ルール
- 既存テスト全パス
- 新規コードにtype hint
- 「案件」を見落とすよりは「skipすべきものをprojectにする」方がマシ（Recall最優先）
"""

task_m = r"""# 【Cursor作業指示】Task M: gate_checker Gemini→Claude Sonnet差替え

対象ディレクトリ: ses_work/gate_checker/
作業内容: 第2レビュアーをGemini→Claude Sonnet 4.6に変更
完了条件: Sonnet呼び出し成功 + テスト
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 背景
Gemini 2.0 Flashの無料枠が完全枯渇（quota=0）。
gate_checkerが実質GPT-4o単独判定になっている。
第2レビュアーをClaude Sonnet 4.6 APIに差し替える。

## 修正箇所

### gate_check.py

1. Gemini呼び出し関数（call_gemini等）をClaude Sonnet呼び出しに差し替え:

```python
def call_sonnet(prompt: str, system: str, env: dict) -> str:
    """Claude Sonnet 4.6を第2レビュアーとして呼び出す"""
    api_key = env.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return ""
    import urllib.request
    import json
    body = json.dumps({
        "model": "claude-sonnet-4-6-20250514",
        "max_tokens": 2000,
        "system": system,
        "messages": [{"role": "user", "content": prompt}]
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            data = json.loads(res.read())
            return data["content"][0]["text"]
    except Exception as e:
        logger.error(f"Sonnet呼び出し失敗: {e}")
        return ""
```

2. 合意判定のラベルを更新: Gemini → Sonnet

3. 結果JSONのキーも更新: gemini_verdict → sonnet_verdict

### システムプロンプト改善

GPTとSonnet両方のシステムプロンプトに追加:
```
## 重要な注意事項
- CostGuardはLLM API呼び出し（OpenAI/Anthropic/Gemini）専用
- Notion API、freee API、LINE Messaging API等の非LLM外部APIはCostGuard対象外
- Notion DBへの読み書きは「自動送信」に該当しない（確認不要）
- 承認済みの仕様変更（soft-skill all-pass、語彙外REVIEW化等）はNG判定しない
```

### CostGuard統合
call_sonnet()にもCostGuardのallowed/finalizeを追加:
block_type="gate_checker", phase="review_sonnet"

### DAILY_CALL_LIMIT
10 → 30に修正（SPEC.md準拠）

## テスト
- Sonnet呼び出しが成功し結果が返ること
- CostGuardでコスト記録されること
- DAILY_CALL_LIMIT=30が反映されていること

---

## 共通ルール
- 既存テスト全パス / 新規コードにtype hint
"""

for fname, content in {
    "20260619_200000_taskL_classify_fix.md": task_l,
    "20260619_200100_taskM_sonnet_gate.md": task_m,
}.items():
    with open(os.path.join(pending, fname), 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"saved: {fname}")

print("\n--- pending_tasks ---")
for f in sorted(os.listdir(pending)):
    if f.startswith('2026'):
        print(f"  {f}")
