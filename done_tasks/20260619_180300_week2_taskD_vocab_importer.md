# 【Cursor作業指示】Week2 Task D: 語彙外スキルREVIEW化 + importer修正

対象ディレクトリ: ses_work/
作業内容: マッチング精度改善 + importer安定化
完了条件: 修正＋テスト追加＋既存テスト全パス
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 修正1: 語彙外必須スキルのREVIEW化

### 問題
matcher.py の judge() で SkillNormalizer.normalize(skill) が None を返す語彙外スキル
（Terraform, SAP, Salesforce等 31件）はチェック対象外 → 必須不足でもMATCH化。

### 修正方針
```python
unknown_skills = []
for skill in required_skills:
    canonical = normalizer.normalize(skill)
    if canonical is None:
        unknown_skills.append(skill)
        continue
    if canonical not in engineer_skill_set:
        missing.append(skill)

if unknown_skills:
    reasons.append(f"語彙外必須スキル要確認: {', '.join(unknown_skills)}")
```

### テスト追加
- 必須「Terraform」（語彙外）→ REVIEW
- 必須「Java」+「SAP」→ JavaマッチかつSAPでREVIEW
- 全必須が語彙外 → REVIEW（NGではない）

---

## 修正2: importer exit 255修正

### 問題
mail_attachment_importer/importer.py が毎回途中クラッシュ。ログ不在。

### 修正方針
1. main()に最上位try/except追加（traceback出力）
2. ログファイルパスを明示設定
3. 処理件数カウンタ追加（何件目で落ちるか特定）
4. 各メール処理失敗は continue で全体を止めない

---

## 共通ルール
- 既存テスト全パス / 新規コードにtype hint
- sys.stdout.reconfigure(encoding='utf-8', errors='replace') をスクリプト冒頭に
