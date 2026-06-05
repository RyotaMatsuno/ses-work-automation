# CLAUDE.md — cost_control（コスト統制基盤）Codex作業ルール

最終更新: 2026-06-05 / 設計: ジョブズ

## 目的
2026-06-02のAPIコスト暴走（1日$50.88・active_projects 5,970件膨張・Anthropic/LINE両上限到達）の
再発防止。止血ではなく構造的ガードレールを実装する。

## 絶対禁止
- 送信系ロジック（メール送信 / LINE push・reply / 提案文の自動送信）には一切触れない。
  notify_line.py・freee送信・成約フローの送信部分は変更不可。
- モデル名のハードコードを新規追加しない。必ず config（env）経由にする。
- 既存の判定ロジック（スキルマッチの NG/REVIEW/MATCH 基準）の数値を勝手に変えない。

## 実装ルール
- .py は先頭に `import sys; sys.stdout.reconfigure(encoding='utf-8', errors='replace')`。
- .bat は ASCII のみ（日本語混入で文字化け）。パスは %~dp0。
- 変更後は `py_compile` で構文確認し、結果を ses_work 直下の .txt に書いてから読む（stderr直読み禁止）。
- Notion大量操作は MCP ではなく REST 直叩き。credential は config/.env を dotenv_values。
- 出力ファイルは ses_work 直下に書く（filesystem MCP がサブディレクトリを読めないため）。
- 各タスク完了時に TASKS.md のチェックボックスを更新する。

## 影響範囲（このSPECで触るファイル）
- mail_pipeline/mail_pipeline.py（取り込みフィルタ・分類上限）
- skill_reader/skill_reader.py（vision/text抽出のモデル）
- outlook/outlook_to_notion.py（分類モデル）
- matching_v2/skill_judge.py（Sonnetフォールバック除去）
- common/ledger.py + matching_v3/cost_guard.py（全スクリプトへ横展開）
- 新規: cost_control/project_expiry.py（案件自動失効）
- 新規: config 集約モジュール（model名の一元管理）

## やってはいけない判断
- 「速いから」とジョブズの設計を待たず勝手に仕様変更しない。SPEC外の最適化は提案に留める。
