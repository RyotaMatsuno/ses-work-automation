# auto_coder TASKS.md v1.0

最終更新: 2026-06-17
対応SPEC: SPEC.md v1.0

---

## Phase 0: 準備
- [ ] 0.1 auto_coder/ ディレクトリ作成(SPEC/TASKS/CLAUDE 配置済み)
- [ ] 0.2 config/.env に ANTHROPIC_API_KEY 確認(既存)
- [ ] 0.3 pip install anthropic(未インストールなら)

## Phase 1: ツール実装(auto_coder/tools.py)
- [ ] 1.1 read_file(path, max_bytes=50KB)
- [ ] 1.2 write_file(path, content) ses_work外拒否
- [ ] 1.3 edit_file(path, old_str, new_str) 一意一致必須
- [ ] 1.4 list_directory(path, max_entries=200)
- [ ] 1.5 run_command(cmd, timeout=120) allowlistチェック
- [ ] 1.6 search_files(pattern, path, glob, max_matches=100)
- [ ] 1.7 パス検証ヘルパ: _validate_path(path, worktree)

## Phase 2: コアループ(auto_coder/agentic_coder.py)
- [ ] 2.1 Anthropic Messages API 呼び出しラッパ(tools定義付き)
- [ ] 2.2 tool use ループ(tool_use -> 実行 -> tool_result -> 再送)
- [ ] 2.3 CostGuard 統合(allowed -> API -> finalize 各ターン)
- [ ] 2.4 完了判定(IMPL_COMPLETE / end_turn / ターン上限 / コスト上限 / タイムアウト)
- [ ] 2.5 安全装置(同一ツール連続検知、ファイルサイズ/出力 truncate)
- [ ] 2.6 監査ログ出力(turns.jsonl / commands.log / files_changed.txt / summary.md)
- [ ] 2.7 エラーハンドリング(API リトライ / auth / bad_request / CostGuard 中断)

## Phase 3: アダプタ(task_auto_runner/claude_invoker.py)
- [ ] 3.1 InvokeResult dataclass 定義
- [ ] 3.2 invoke(task_path, worktree, timeout) -> InvokeResult
- [ ] 3.3 task_auto_runner/runner.py の最小修正(InvokeResult 対応)

## Phase 4: テスト
- [ ] 4.1 test_read_file.py
- [ ] 4.2 test_write_file.py
- [ ] 4.3 test_edit_file.py
- [ ] 4.4 test_run_command.py
- [ ] 4.5 test_search_files.py
- [ ] 4.6 test_agentic_loop.py(mock API)
- [ ] 4.7 test_cost_guard_integration.py
- [ ] 4.8 test_invoke_result.py
- [ ] 4.9 全テスト PASS 確認

## Phase 5: 統合テスト(手動)
- [ ] 5.1 実 API で簡単なタスク実行
- [ ] 5.2 pending_tasks/ -> task_auto_runner -> done/ 確認
- [ ] 5.3 失敗3回 -> blocked/ 確認
- [ ] 5.4 CostGuard 記録確認
- [ ] 5.5 監査ログ確認

## Phase 6: ゲート2(ジョブズ担当)
- [ ] 6.1 GPT-5.4 コードレビュー
- [ ] 6.2 GO 判定

---

## 変更履歴
| 日付 | 内容 |
|---|---|
| 2026-06-17 | v1.0 初版 |