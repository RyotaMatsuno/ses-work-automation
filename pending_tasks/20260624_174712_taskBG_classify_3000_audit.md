# 【Cursor作業指示】Task BG: 分類精度改善（GPT-5.4 3ラウンド合意版）

対象: ses_work/mail_pipeline/
参照: CLAUDE.md / mail_pipeline/mail_pipeline.py / mail_pipeline/raw_inbox.db
完了条件: 人員混入率を明確に低下させ、案件取りこぼしを悪化させない
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## Phase 1: 200件評価セット作成

### 1-1. 層化抽出（mail_pipeline/analysis/build_eval_set.py 新規）
raw_inbox.dbから200件を以下の配分で抽出:
- project判定: 80件（直近50% + 過去ランダム30% + 高リスクKW上乗せ20%）
- engineer判定: 60件（同配分）
- skip判定: 40件（同配分）
- 混在/曖昧: 20件

高リスクKWの分類:
- engineer強シグナル: 要員, 経歴書, スキルシート, 並行営業可, 提案可, 人材配信
- project強シグナル: 案件, 単価, 面談, 募集枠, 業務内容
- 曖昧シグナル: 稼働, SE経験, PMO人材, 常駐可

### 1-2. ラベル定義（メール単位で三値）
```python
# 各メールに以下を付与
{
    "contains_project": true/false,  # 案件情報を含むか
    "contains_engineer": true/false, # 人材情報を含むか
    "primary_type": "project" / "engineer" / "skip" / "mixed" / "other",
    "review_needed": true/false
}
```
- 1通に案件+人材が混在するケースは primary_type="mixed"

### 1-3. 評価セット出力
`mail_pipeline/analysis/eval_set_200.json` に保存

## Phase 2: 分類改善（2層構成）

### 2-1. 第1層: ルールベース（analyze_final.py修正）
ルール判定結果を離散カテゴリに分類:
- strong_project: 案件確定（案件テンプレ語2個以上、STRONG_PROJECT一致等）
- strong_engineer: 人材確定（以下のパターン）
  - 「若手/ベテラン/中堅/シニア + 人材/エンジニア/技術者」
  - 「人材/要員 + 紹介/ご紹介/配信」
  - 「NN歳/男性/女性」プロフィール形式
  - 「弊社プロパー/フリーランス + 紹介/ご案内」
  - 「おすすめ人材/注力要員」
  - 「スキルシート送付/経歴書添付」
- ambiguous: 上記どちらにも確定しない

※confidence数値ではなく離散カテゴリで判定（GPT合意: 校正されていない数値よりMVP向き）

### 2-2. 第2層: LLM再分類（ambiguousのみ）
- ambiguous判定のメールのみgpt-4.1-nanoで再分類
- CostGuard管理下（phase="classify"の予算を使用）
- 再分類結果 + 理由文字列を保存

### 2-3. テスト追加
- `mail_pipeline/tests/test_task_bg_eval.py`（新規）
- 200件評価セットから代表15件をテストケース化
- 既存テスト30/30が壊れないこと

## Phase 3: DB反映

### 3-1. 案件DBプロパティ追加
- classification_reason (rich_text)
- classification_version (rich_text)
- review_needed (checkbox)
- is_active_for_matching (checkbox, default true)

### 3-2. inactive化ルール（慎重運用）
- strong_engineer + 案件シグナルがほぼなし → is_active_for_matching=false
- それ以外 → 保留（review_needed=trueのみ付与）
- **inactive化適用前にstrong_engineer判定群のspot check必須**（GPT注意点）

### 3-3. matching_v3側の対応
- is_active_for_matching=trueの案件のみマッチング対象

## 完了条件
- [ ] 200件評価セット生成
- [ ] ルール1層目（strong_project/strong_engineer/ambiguous）実装
- [ ] LLM2層目（ambiguousのみ再分類）実装
- [ ] 200件ベンチマークで修正前後比較
- [ ] 新規テスト+既存テスト全PASS
- [ ] DB反映（プロパティ追加+inactive慎重適用）
