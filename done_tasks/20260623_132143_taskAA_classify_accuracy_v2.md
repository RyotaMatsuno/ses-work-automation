# 【Cursor作業指示】Task AA: 分類精度本格改善（280件ベンチマーク+GPT分析ベース）

対象ファイル: ses_work/analyze_final.py
作業内容: GPT-5.4分析に基づく7項目の精度改善を実装
参照ファイル: CLAUDE.md / research_results/GPT_CLASSIFY_ACCURACY_280_20260623.md
完了条件: 280件ベンチマークで project→engineer混入 2%以下 + skip→project損失 3件以下
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 現状（280件ベンチマーク）
- project→engineer混入: 14/120 (12%) ← 最大の問題
- skip→project損失: 10/80 (13%) ← 案件の取りこぼし
- project→other誤分類: 7/120 (6%)
- ルール全体一致率: 64.6%

## 目標
- project→engineer混入: ≤2% (120件中2件以下)
- skip→project損失: ≤3件
- project→other誤分類: ≤2件
- ルール全体一致率: ≥80%

---

## 改善1: ENGINEER_PATTERNS強化（IMP-1）
件名冒頭の人材売り込み定型を追加。eng_score +5（最優先）にする。

追加パターン:
```python
# === 件名定型（eng_score +5: project語があっても人材優先） ===
r"直フリーランス",
r"(?:1社下|1社先|弊社1社下)",
r"(?:弊社福岡プロパー|弊社社員|弊社要員)",
r"【\d{1,2}月人材】",
r"(?:ご紹介可能|提案可能|要員紹介|人材紹介|要員提案)",
r"(?:スキルシート|職務経歴書|経歴書|ご経歴)",
```

## 改善2: BODY_ENGINEER_STRONG強化（IMP-2）
本文中の人材紹介フォーマット検出を追加。

追加パターン:
```python
r"(?:氏名|年齢|性別|国籍|所属|最寄|稼働率|並行)\s*[:：]",  # 構造化項目3つ以上でstrong
r"(?:スキルシート|職務経歴書|経歴書)\s*(?:添付|送付|共有)",
r"(?:ご提案させていただきます|ご紹介いたします|ご紹介させていただきます)",
r"(?:保有スキル|経験年数|希望単価|稼働開始日)\s*[:：]",
```
注意: 構造化項目は**3つ以上マッチ**した場合のみ eng+4。1-2個は案件側にもあるので無視。

## 改善3: スコアリング優先判定（IMP-3）
classify_by_ruleの判定ロジックに優先ルール追加:

```python
# Engineer強シグナル優先:
# ① 件名定型ヒット(+5) + body人材ヒット → proj_scoreに関係なくengineer
# ② ただしproject構造語（案件概要/業務内容/募集人数/面談回数/勤務地/精算/商流）が3個以上 → 再比較
```

## 改善4: 弱フォールバック厳格化（IMP-4）
```python
# 変更前:
if score >= 2:
    for pat in PROJECT_PATTERNS:
        if re.search(pat, subj):
            return "project"

# 変更後:
if score >= 2 and eng_score == 0:  # engineerヒットゼロの場合のみフォールバック
    proj_pattern_hits = sum(1 for pat in PROJECT_PATTERNS if re.search(pat, subj))
    if proj_pattern_hits >= 2:  # 2パターン以上マッチ必須
        return "project"
```

## 改善5: skip先行確定の抑制（IMP-5）
```python
# 変更前:
for pat in SKIP_PATTERNS:
    if re.search(pat, subj + " " + frm):
        return "skip"

# 変更後:
SES_STRONG_KEYWORDS = r"案件|募集|Java|PHP|Python|AWS|Azure|NW|インフラ|PMO|SpringBoot|React|Vue|SAP|COBOL|C#"
for pat in SKIP_PATTERNS:
    if re.search(pat, subj + " " + frm):
        if not re.search(SES_STRONG_KEYWORDS, subj):
            return "skip"
        # SES語がある → skipせずスコアリングへ
```

## 改善6: PROJECT_PATTERNS構造語追加（IMP-6）
```python
r"(?:注力案件|最注力案件)",
r"(?:案件概要|業務内容|担当工程|開発環境)",
r"(?:面談(?:回数)?|精算|商流|作業場所)",
```

## 改善7: OTHER_PATTERNS抑制（IMP-7）
SES文脈語（案件/万/募集/開発）がある場合はother確定を抑制:
```python
# other判定の前にガード追加
if re.search(r'案件|募集|開発|\d+万|設計|構築|運用', subj):
    pass  # other判定をスキップ
else:
    for pat in OTHER_PATTERNS:
        ...
```

## テスト
1. 既存テスト(test_task_y_classify.py)が全PASS
2. **280件ベンチマーク再実行**: `tmp_benchmark_retest.py` を作成
   - project→engineer: ≤2%
   - skip→project: ≤3件
   - project→other: ≤2件
3. 不一致パターンの件名サンプル20件を出力して目視確認可能にする

## ベンチマークデータ
ses_work/mail_pipeline/raw_inbox.db の以下SQLでサンプリング:
```sql
SELECT subject, sender, body_text, classify_result
FROM raw_emails
WHERE classify_result IN ('project','skip','other','engineer')
ORDER BY RANDOM()
LIMIT 280
-- seed=42 で再現可能にするためPythonのrandom.seed(42)を使用
```

## 禁止事項
- project精度（77% = 92/120）を70%未満に下げない
- engineer検出率（100% = 20/20）を下げない
- LLMコールを追加しない（ルールベースのみ）
