# 【Cursor作業指示】matching_v3: P1 スキル正規化ルール（高信頼パターンのみ）

## 対象
ses_work/matching_v3/

## 背景
P-1計測でALL_REQUIRED_SKILLS_OOVが353件落下。
GPT-5.4壁打ちで「一律suffix stripは危険、高信頼パターンのみに限定すべき」と指摘済み。

## 作業内容

### 1. skill_gate.pyに正規化前処理を追加

新規関数: normalize_skill_text(raw_skill: str) -> str

#### ルールカテゴリ1: 技術名+経験（高信頼）
パターン: /^(Java|Python|PHP|C#|AWS|Azure|GCP|React|Vue|Angular|Docker|Kubernetes|Linux|Oracle|MySQL|PostgreSQL|SQL|Spring|TypeScript|JavaScript|Node\.js|Go|Ruby|Kotlin|Swift|Terraform|Jenkins|Salesforce|COBOL|VBA|Excel|Word|PowerShell|Shell|HTML|CSS)[経験実績]$/
→ 技術名のみを返す
例: "Java経験" → "Java", "AWS実績" → "AWS"

#### ルールカテゴリ2: 技術名+動詞+経験（高信頼）
パターン: /^(Java|Python|...同上)[開発設計構築運用保守導入移行]+経験$/
→ 技術名のみを返す
例: "Java開発経験" → "Java", "AWS構築経験" → "AWS"

#### ルールカテゴリ3: 工程名+経験（中信頼、process_skillsへ振り分け）
パターン: /^(要件定義|基本設計|詳細設計|製造|テスト|運用|保守)経験$/
→ 工程名を返す（tech_skillではなくprocess_skillとして扱う）
例: "要件定義経験" → "要件定義"(→process_skills.jsonに追加)

#### 適用しないパターン（低信頼）
以下はsuffix stripしない:
- "知識" "スキル" "対応可" "案件" "業務"
- 例: "Java知識" → そのまま（OOVのままでよい）

### 2. 適用タイミング
- denylistチェックの後、alias解決の前に実行
- 正規化前後のディフをログ出力

### 3. process_skills.json拡充
以下を追加:
- 要件定義
- 基本設計
- 詳細設計
- 製造
- テスト
- 運用
- 保守
- リーダー
- PM/PL
- 上流工程

### 4. テスト
- カテゴリ1/2/3の各パターンで正規化が正しく動作
- 低信頼パターンが変換されないこと
- 既存テストが通る

### 5. 効果測定
pipeline_measure.pyでP1適用前後の差分を計測:
- ALL_REQUIRED_SKILLS_OOVの件数変化
- 最終マッチ数の変化

## 参照
- CLAUDE.md
- matching_v3/skill_gate.py
- config/process_skills.json
- config/denylist.json
- logs/unknown_skill_candidates/

## 完了条件
- [ ] normalize_skill_text()が3カテゴリのルールで正規化
- [ ] 低信頼パターンは変換しない
- [ ] process_skills.jsonに工程名が追加
- [ ] テスト追加・既存テスト通過
- [ ] pipeline_measureで効果測定済み

## 質問がある場合
Claude.aiチャットに貼り付けて確認
