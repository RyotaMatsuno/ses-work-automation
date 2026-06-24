# auto_coder CLAUDE.md v1.0

最終更新: 2026-06-17

## 目的
Anthropic Messages API を直接叩く自動コーディングエージェント。
Claude Code CLI の代替として、pending_tasks/ の指示書を自動実装する。

## 作業ルール
- SPEC.md / TASKS.md を必ず先に読む
- 既存の task_auto_runner/runner.py は最小修正のみ(アダプタ方式)
- claude_invoker.py は全面書き換え(InvokeResult 返却)
- agentic_coder.py / tools.py / config.py は新規作成
- UTF-8 固定、日本語パスを cwd に渡さない
- common/io_utils.py の setup_stdout() を使う

## 禁止事項
- CostGuard なしの Anthropic API 呼び出し
- ses_work/ 外への書き込み
- run_command の allowlist 外コマンド実行
- task_auto_runner の 5分スキャン / 3回リトライ / blocked 退避ロジックの変更
- 全面書き換えより部分編集を優先(既存ファイルの構造を壊さない)

## テスト
- pytest でツール単体テスト + ループテスト(mock API)
- 実 API テストは手動(コスト発生のため自動テストに含めない)

## 変更履歴
| 日付 | 内容 |
|---|---|
| 2026-06-17 | v1.0 初版 |