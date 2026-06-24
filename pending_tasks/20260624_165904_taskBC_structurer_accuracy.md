# 【Cursor作業指示】Task BC: 構造化精度改善（スキル/単価/勤務地抽出）

対象ディレクトリ: ses_work/matching_v3/
作業内容: 案件メールからの情報抽出精度を向上（売上直結領域）
参照ファイル: CLAUDE.md / matching_v3/structurer.py / matching_v3/skill_aliases.json
完了条件: 抽出スキーマ厳格化・正規化辞書拡張・信頼度スコア付与
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 背景（GPT-5.4壁打ち合意済み）
- 分類精度は目標達成（oracle 4.75%）。次のボトルネックは構造化精度
- 「matching精度が悪い原因の多くは実はextract精度」（GPT指摘）
- 必須スキル/単価/勤務地の抽出が崩れるとマッチングの土台が壊れる

## 変更内容

### 1. 抽出スキーマ厳格化（structurer.py）

LLMプロンプトの出力スキーマを以下に統一:
```json
{
  "must_have_skills": ["Java", "Spring Boot"],
  "nice_to_have_skills": ["AWS", "Docker"],
  "budget_min": 65,
  "budget_max": 70,
  "budget_text": "65〜70万円",
  "location": "東京都港区",
  "location_normalized": "東京",
  "remote_type": "hybrid",
  "start_date": "2026-08",
  "period": "長期",
  "interview_count": 2,
  "nationality_ok": false,
  "age_limit": null,
  "headcount": 1
}
```
- 未抽出フィールドはnull（空文字列やデフォルト値ではなくnull）
- 数値フィールドは数値型（文字列禁止）

### 2. 勤務地正規化辞書（matching_v3/location_aliases.json 新規作成）
```json
{
  "東京": ["東京都", "都内", "23区", "港区", "千代田区", "新宿", "渋谷", "品川", "大手町", "六本木", "五反田", "秋葉原", "池袋", "汐留", "霞ヶ関", "虎ノ門"],
  "横浜": ["横浜市", "神奈川", "みなとみらい", "関内"],
  "大阪": ["大阪府", "大阪市", "梅田", "本町", "淀屋橋"],
  "名古屋": ["名古屋市", "愛知", "栄", "名駅"],
  "リモート": ["フルリモート", "在宅", "テレワーク"]
}
```

### 3. 単価正規化ロジック（structurer.py内）
以下のパターンを数値に変換:
- "70万前後" → budget_min=67, budget_max=73
- "スキル見合い" → budget_min=null, budget_max=null
- "80-90万" → budget_min=80, budget_max=90
- "〜70万" → budget_min=null, budget_max=70
- "70万〜" → budget_min=70, budget_max=null

### 4. スキル正規化辞書の拡張（skill_aliases.json）
現行182→目標250正規スキル:
追加候補: SAP, Salesforce, ServiceNow, COBOL, VB.NET, Unity, Flutter, Terraform, Kubernetes, Jenkins, GitLab CI, Ansible, Datadog, Splunk, etc.

### 5. 抽出結果の信頼度スコア（オプション）
- 各フィールドにconfidenceを付与（0.0〜1.0）
- 低信頼度（<0.5）のフィールドはNotionに「要確認」フラグ

## テスト
1. 代表的な案件メール10件で抽出結果を検証
2. 単価パターン変換の単体テスト
3. 勤務地正規化の単体テスト
4. skill_aliases.jsonの拡張後に既存テスト全PASS
