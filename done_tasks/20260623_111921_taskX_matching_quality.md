# 【Cursor作業指示】Task X: マッチング品質修正+line_query統合（P0-5/P0-6/P0-4）

対象ディレクトリ: ses_work/
作業内容: スキルマッチ判定バグ修正 + line_queryモジュール統合
参照ファイル: CLAUDE.md / INVESTIGATION_REPORT.md / matching_v3/skill_aliases.json
完了条件: 全テスト通過 + 誤マッチ0件（java/javascript, sql/mysql）
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## P0-5: 逆マッチング必須スキルALL判定統一
場所: line_webhook/webhook_server.py:535-537, line_query/line_query.py:360-362

現状の問題:
- 逆マッチング(案件→エンジニア検索)で必須スキルが ANY 判定（1つ一致で通過）
- 順マッチング(run_matching)は ALL 判定
- 非対称のため偽陽性が発生

修正内容:
1. 全マッチング経路で必須スキルを ALL-required に統一
2. `required_skills` の全項目がエンジニアスキルに含まれる場合のみMATCH
3. `#skill_skip` タグ付きエンジニアはスキルフィルタをバイパス（既存ルール維持）

## P0-6: skill_utils部分文字列マッチ廃止
場所: line_webhook/skill_utils.py:57-60

現状の問題:
- `java` in `javascript` → True（偽陽性）
- `sql` in `mysql` → True（偽陽性）
- `c` in `c#` → True（偽陽性）

修正内容:
1. 部分文字列マッチを完全一致+エイリアステーブルに変更
2. matching_v3/skill_aliases.json のエイリアスマップを共有利用
3. 正規化: 全角→半角、大文字→小文字、トリム
4. トークン境界を考慮（"C#"と"C"は別、"React"と"React Native"は別）

テスト:
- java ≠ javascript
- sql ≠ mysql
- c ≠ c#
- react ≠ react native
- python == Python == PYTHON（正規化）
- java == Java == JAVA（正規化）

## P0-4: line_query importの統一
場所: line_webhook/webhook_server.py:1752-1753, 1788

現状の問題:
- 本番webhookが `line_query/line_query.py` (古い版)をimport
- `line_webhook/line_query.py` の新機能（詳細コマンド、鮮度フィルタ、表示上限）が未適用

修正内容:
1. webhook_server.py のimportを `line_webhook.line_query` に変更
2. 旧 `line_query/line_query.py` を参照するコードがないことを確認
3. Cloud Run デプロイ時に正しいモジュールが含まれることを確認

注意: Cloud Runデプロイは松野の手動操作。Cursorはコード修正のみ。
