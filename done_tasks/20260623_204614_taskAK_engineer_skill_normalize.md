# 【Cursor作業指示】Task AK: エンジニアDBスキル正規化バッチ

対象: ses_work/matching_v3/ + ses_work/scripts/
参照: CLAUDE.md / skill_aliases.json / matcher.py
完了条件: normalize_engineer_skills.py が動作し、エンジニアの生スキルをcanonical化

## 背景
エンジニアDBのスキルは手入力で表記ゆれが多い（「java」「JAVA」「Java8」「Java/Spring」等）。
matcher.pyのjudge()はeng_skillsをnormalize_hardで正規化するが、事前バッチで一括正規化する方が効率的。

## 変更
1. scripts/normalize_engineer_skills.py 新規作成
   - Notion APIでエンジニアDB全件のスキルプロパティを取得
   - skill_aliases.json を使って各スキルをcanonical化
   - 正規化前→正規化後のマッピングをログ出力（変更なしはスキップ）
   - --dry-run オプションで変更内容をプレビュー
2. matcher.py の eng_skills 構築ロジックで、Notion側に正規化済みフィールドがあればそちらを優先
3. 正規化カバレッジを計算（全スキル語彙中、辞書でカバーされた割合）

## 実行方法
python scripts/normalize_engineer_skills.py --dry-run  # プレビュー
python scripts/normalize_engineer_skills.py              # 実行

## 禁止
- Notionのスキルプロパティを直接上書きしない（別フィールドに保存 or ログのみ）
- CostGuardなしでLLMを呼び出さない
