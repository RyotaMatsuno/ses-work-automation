# auto_coder SPEC v1.0

最終更新: 2026-06-17 / バージョン: v1.0

---

## 0. 概要

Claude Code CLI が対話モード前提(v2.1.144)となり、--dangerously-skip-permissions が Edit/Write を抑止しなくなった。
Anthropic Messages API を直接叩き、CLI に依存しない自動コーディング装置を構築する。

目標: pending_tasks/ に指示書を置くだけで自動実装が走る。松野は LINE/Claude だけで業務完結。

---

## 1. アーキテクチャ(アダプタ方式、GPT-5.4 推奨)

### 1.1 全体構成

task_auto_runner.py(既存維持、5分スキャン)
  -> claude_invoker.py(差し替え: CLI呼び出し -> agentic_coder 呼び出し)
    -> agentic_coder.py(新規: Anthropic Messages API + tool use ループ)
      -> ツール群(read_file / write_file / edit_file / list_directory / run_command / search_files)

### 1.2 変更範囲

| ファイル | 変更内容 |
|---|---|
| task_auto_runner/claude_invoker.py | 全面書き換え(薄いアダプタ) |
| auto_coder/agentic_coder.py | 新規(コア) |
| auto_coder/tools.py | 新規(ツール定義 + 実行) |
| auto_coder/config.py | 新規(設定) |
| task_auto_runner/runner.py | 最小修正(InvokeResult 対応) |

### 1.3 既存維持(変更なし)

- task_auto_runner の 5分スキャン / 3回リトライ / blocked 退避 / done 移動
- pending_tasks/ のファイル名規約
- LINE 通知(完了/失敗)

---

## 2. agentic_coder.py コア仕様

### 2.1 エントリポイント

def run_task(task_path: Path, worktree: Path) -> InvokeResult
  指示書を読み、tool use ループで自動実装し、結果を返す。

### 2.2 tool use ループ

1. system prompt + 指示書テキスト -> Messages API(tools 付き)
2. レスポンスに tool_use があれば実行 -> tool_result を返す
3. stop_reason == "end_turn" まで繰り返す
4. 完了判定(2.5)

### 2.3 Messages API 呼び出し仕様

| パラメータ | 値 |
|---|---|
| model | claude-sonnet-4-6 |
| max_tokens | 16384 |
| tools | 3 のツール定義(6個) |
| system | 4 の system prompt |

### 2.4 CostGuard 統合

各ターンの API 呼び出しで:
1. cost_guard.allowed(phase="heavy", block_type="auto_coder", target_id=task_id, script="agentic_coder") で事前チェック
2. API 呼び出し実行
3. cost_guard.finalize(decision, in_tokens=usage.input_tokens, out_tokens=usage.output_tokens, success=True/False, error_kind=...) で記録
4. allowed=False -> タスク中断、retryable_error で返却

### 2.5 完了判定(優先順)

1. モデル最終テキストに IMPL_COMPLETE 含む -> success
2. stop_reason=end_turn かつ直前ターンでファイル更新あり -> success(ただし IMPL_COMPLETE なしは warning)
3. ターン上限到達 -> retryable_error
4. コスト上限到達 -> retryable_error
5. タイムアウト -> retryable_error
6. API エラー(transient) -> retryable_error
7. API エラー(permanent) -> fatal_error

### 2.6 安全装置

| 装置 | 値 | 超過時 |
|---|---|---|
| 最大ターン数 | 25 | 中断、retryable_error |
| 1タスクあたり最大コスト | $2.00 | 中断、retryable_error |
| タイムアウト | 30分 | 中断、retryable_error |
| 同一ツール連続呼び出し | 3回 | 強制 end_turn 促し |
| ファイルサイズ上限(read) | 50KB | truncate + 通知 |
| コマンド出力上限 | 20KB | truncate + 通知 |

---

## 3. ツール定義

### 3.1 read_file
- path: str (relative from worktree)
- 50KB超は truncate、truncated=true を返す

### 3.2 write_file
- path: str, content: str
- ses_work/ 外は拒否
- 親ディレクトリ自動作成

### 3.3 edit_file
- path: str, old_str: str, new_str: str
- old_str は一意かつ完全一致必須
- 不一致 / 複数一致はエラー返却(中断しない)

### 3.4 list_directory
- path: str (default ".")
- 最大200件

### 3.5 run_command
- command: str, timeout: int (default 120, max 300)
- allowlist: python, pytest, git status, git diff
- 出力20KB truncate

### 3.6 search_files
- pattern: str (regex), path: str, glob: str (default *.py)
- 最大100マッチ

---

## 4. system prompt

あなたは自動コーディングエージェントです。指示書に従ってコードを実装してください。

ルール:
- 作業ディレクトリは ses_work/ 配下のみ
- 必ず既存コードを read_file で読んでから edit_file/write_file で編集する
- 最小変更を優先する(全面書き換えより部分編集)
- テスト可能な場合は run_command で pytest を実行する
- 失敗時はエラー出力を読んで原因を特定し、修正を試みる
- 完了時は最後に IMPL_COMPLETE と出力する
- 不明点があっても停止せず、合理的仮定で前進する
- 破壊的変更(既存ファイルの全削除等)は禁止
- 日本語でサマリを出力する
- ses_work/ 外への書き込み禁止
- UTF-8 エンコーディング固定

---

## 5. claude_invoker.py アダプタ仕様

### 5.1 InvokeResult dataclass

- success: bool
- status: str (success / retryable_error / fatal_error)
- summary: str
- turns: int
- cost_usd: float
- files_changed: list[str]
- test_summary: str
- raw_output: str

### 5.2 invoke() インターフェース

def invoke(task_path: Path, worktree: Path, timeout: int = 1800) -> InvokeResult
  task_auto_runner から呼ばれるエントリポイント。

---

## 6. 監査ログ

タスクごとに logs/auto_coder/{task_id}/ を作成:

| ファイル | 内容 |
|---|---|
| instruction.md | 指示書コピー |
| turns.jsonl | 各ターンの request/response 要約 |
| commands.log | run_command の出力 |
| files_changed.txt | 変更ファイル一覧 |
| summary.md | 最終サマリ + コスト + ターン数 |
| git_diff.txt | 実行前後の git diff |

---

## 7. エラーハンドリング

| エラー種別 | 対応 | status |
|---|---|---|
| API 429/500/503 | 3回リトライ(指数バックオフ 5/15/45秒) | retryable_error |
| API 400 | 即中断 | fatal_error |
| API 401 | 即中断 | fatal_error |
| CostGuard allowed=False | 即中断 | retryable_error |
| ターン上限 | 即中断 | retryable_error |
| コスト上限 | 即中断 | retryable_error |
| タイムアウト | 即中断 | retryable_error |
| ツール実行エラー | tool_result でモデルに返す | - |
| write_file パス違反 | tool_result でエラー | - |
| run_command 非 allowlist | tool_result でエラー | - |

---

## 8. 設定(auto_coder/config.py)

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 16384
MAX_TURNS = 25
MAX_COST_PER_TASK_USD = 2.00
TASK_TIMEOUT_SEC = 1800
READ_FILE_MAX_BYTES = 50 * 1024
COMMAND_OUTPUT_MAX_BYTES = 20 * 1024
COMMAND_TIMEOUT_SEC = 120
COMMAND_ALLOWLIST = ["python", "pytest", "git status", "git diff"]
SAME_TOOL_REPEAT_LIMIT = 3

---

## 9. テスト計画(Phase 4)

| # | テスト | 内容 |
|---|---|---|
| 1 | test_read_file.py | 正常読み取り / 50KB truncate / 存在しないファイル |
| 2 | test_write_file.py | 新規作成 / 上書き / ses_work 外拒否 / 親ディレクトリ自動作成 |
| 3 | test_edit_file.py | 正常置換 / old_str 不一致エラー / 複数一致エラー |
| 4 | test_run_command.py | allowlist 許可 / 非 allowlist 拒否 / タイムアウト / 出力 truncate |
| 5 | test_search_files.py | 正常検索 / 100件上限 |
| 6 | test_agentic_loop.py | mock API でツールループ正常完了 / ターン上限 / コスト上限 / 同一ツール連続 |
| 7 | test_cost_guard_integration.py | allowed=False 時の中断 / finalize 呼び出し確認 |
| 8 | test_invoke_result.py | InvokeResult の各フィールド検証 |

---

## 10. 変更履歴

| 日付 | バージョン | 内容 |
|---|---|---|
| 2026-06-17 | v1.0 | 初版。GPT-5.4 壁打ち結果を反映。アダプタ方式 / 6ツール / 25ターン上限 / CostGuard統合 / 監査ログ |
