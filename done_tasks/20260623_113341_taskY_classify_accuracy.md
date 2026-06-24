# 【Cursor作業指示】Task Y: パイプライン分類精度改善（other=0%問題）

対象ディレクトリ: ses_work/
対象ファイル: analyze_final.py
作業内容: other（ニュースレター・商材）の分類精度を0%→60%以上に改善
参照ファイル: CLAUDE.md / INVESTIGATION_REPORT.md / research_results/INVESTIGATION_CLASSIFY_ACCURACY_20260622.md
完了条件: テストB再実行で other精度≥60% かつ project精度≥80% を維持
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 根本原因

`classify_by_rule()` の末尾フォールバック（L259-262）:
```python
for pat in PROJECT_PATTERNS:
    if re.search(pat, subj):
        return "project"
return "unknown"
```

PROJECT_PATTERNS に `r"[0-9]+万"`, `r"募集|常駐|増員"`, `r"SES|派遣"` 等の広すぎるパターンがあり、
ニュースレター・商材・告知メールも全て project に吸い込まれる。
→ other は決して返されない。

## 修正方針（3段階）

### Step 1: OTHER_PATTERNS 新設
analyze_final.py に OTHER_PATTERNS を追加。以下のカテゴリを捕捉:
- 商材紹介: `r"商材.*ご紹介|ツール.*紹介|サービス.*のご案内|導入.*ご案内"`
- 営業系: `r"営業支援|リード獲得|マーケティング|営業代行|集客"`
- イベント告知: `r"開催.*のお知らせ|開催日|参加.*無料|参加費"`
- セミナー拡張: `r"商談.*方法|AIで.*標準化|業務.*効率化.*セミナー"`
- 求人広告: `r"掲載.*求人|求人広告|リクナビ|マイナビ|Indeed"`

### Step 2: classify_by_rule フォールバック修正
末尾のフォールバックを以下に変更:
```python
# Step 4: OTHER check（skip_patternsに入れるほど強くないノイズ系）
for pat in OTHER_PATTERNS:
    if re.search(pat, subj + " " + body_head[:500]):
        return "other"

# Step 5: Weak project fallback（2つ以上のシグナル必須に強化）
_, _, _, score = project_signal_score(subj)
if score >= 2:
    for pat in PROJECT_PATTERNS:
        if re.search(pat, subj):
            return "project"

return "unknown"
```

重要な変更点:
- OTHER判定をprojectフォールバックの**前**に配置
- 弱いprojectフォールバックは `score >= 2`（2つ以上のシグナル）を必須に
- `[0-9]+万` 単独ではproject判定しない（score=1ではフォールバック不発火）

### Step 3: テスト追加
`mail_pipeline/tests/test_task_y_classify.py` を新規作成:

```python
# other → other のテストケース（Investigation Reportの誤分類事例から）
OTHER_CASES = [
    ("【明日12時】商談準備〜実施を、AIで標準化する方法", "other"),
    ("【無料ウェビナー】営業効率化のご案内", "skip"),  # skip patterns
    ("SES企業向けマッチングツールのご紹介", "other"),
    ("貴社の採用を支援するサービスのご案内", "other"),
]

# project → project が維持されるテストケース
PROJECT_CASES = [
    ("【案件】Java/Spring 基本設計〜 60万〜", "project"),
    ("PMO案件 7月〜 フルリモート 85万", "project"),
    ("【BTM案件】M365 大手町", "project"),
]

# engineer → engineer が維持されるテストケース
ENGINEER_CASES = [
    ("【SasaTech 人材】TypeScript/Go 90万", "engineer"),
    ("★★おすすめ人材！Python【フリテク押田】", "engineer"),
    ("【弊社プロパー】Java 5年 45万", "engineer"),
]
```

## 禁止事項
- SKIP_PATTERNS を変更しない（既に安定している）
- ENGINEER_PATTERNS を変更しない（直前のv3改修で安定化済み）
- project精度を80%未満にしない（案件取り漏らしは営業損失に直結）
- bodyスコアリングのウェイトを変更しない
