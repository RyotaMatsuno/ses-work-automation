# SPEC.md — ジョブズ コマンドサーバー 仕様書

最終更新: 2026-05-08

## 目的
Claude Desktop（ジョブズ）がローカルPCのターミナル操作を完全自律で実行できるようにする。
松野CEOがターミナルに入力する作業をゼロにすることがゴール。

## システム構成

```
Claude Desktop（ジョブズ）
  ↓ MCP tool call
mcp_bridge.py（MCPサーバー）
  ↓ HTTP POST localhost:8765
command_server.py（HTTPサーバー）
  ↓ subprocess
Windows ターミナル（任意のコマンド実行）
  ↓ stdout/stderr
結果をジョブズに返す
```

## 機能仕様

### command_server.py（HTTPサーバー）

#### 基本仕様
- バインド: `127.0.0.1:8765`（localhost限定）
- 認証: `X-Auth-Token: jobz-terra-2026` ヘッダー必須
- 文字コード: UTF-8
- ログ: `server.log` に全リクエスト記録

#### エンドポイント

| メソッド | パス | 説明 |
|---|---|---|
| GET | /health | 死活確認。トークン不要。 |
| POST | /run | コマンド実行 |
| POST | /write_and_run | ファイル書き込み→実行 |

#### POST /run
```json
// リクエスト
{
  "cmd": "python matching.py",        // 必須: 実行コマンド
  "cwd": "C:\\...\\ses_work",         // 省略可: 実行ディレクトリ（デフォルト: ses_work）
  "timeout": 60                        // 省略可: タイムアウト秒（デフォルト: 60）
}

// レスポンス（成功）
{
  "stdout": "...",
  "stderr": "...",
  "returncode": 0,
  "cmd": "python matching.py"
}

// レスポンス（エラー）
{
  "error": "エラー内容",
  "cmd": "python matching.py"
}
```

#### POST /write_and_run
```json
// リクエスト
{
  "filepath": "C:\\...\\script.py",   // 必須: 書き込み先フルパス
  "content": "print('hello')",        // 必須: ファイル内容
  "run_cmd": "python script.py",      // 省略可: 書き込み後に実行するコマンド
  "cwd": "C:\\...\\ses_work"          // 省略可: 実行ディレクトリ
}

// レスポンス
{
  "filepath": "C:\\...\\script.py",
  "written": true,
  "stdout": "...",      // run_cmd指定時のみ
  "stderr": "...",      // run_cmd指定時のみ
  "returncode": 0       // run_cmd指定時のみ
}
```

### mcp_bridge.py（MCPブリッジ）

#### MCPツール定義

| ツール名 | 説明 |
|---|---|
| run_command | /run エンドポイントへのブリッジ |
| write_and_run | /write_and_run エンドポイントへのブリッジ |

#### Claude Desktop への登録
`claude_desktop_config.json` の `mcpServers` に `jobz-command` として登録済み。

### start_server.bat（起動スクリプト）

- `pythonw`で起動（ターミナルウィンドウを表示しない）
- 起動前に8765ポートのLISTENINGプロセスを全てkillしてから起動（多重起動防止）
- Windowsスタートアップフォルダへのショートカット登録で自動起動
- PC再起動後はターミナル操作なしでジョブズがコマンド実行可能

#### トラブル：多重起動による接続障害（2026-05-08 発生・解決済み）
- **症状**: Claude Desktopからjobz-commandに繋がらない（WinError 10061）
- **原因**: 過去のプロセスが死なずに残り、8765ポートを複数プロセスが掴んでいた
- **解決**: taskkillで旧プロセスを手動kill → start_server.batを改修（起動前に自動kill）
- **再発防止**: bat改修により以降は自動解消される

## セキュリティ仕様
- localhost（127.0.0.1）以外からのリクエストは403で拒否
- 認証トークンなしのリクエストは401で拒否
- 実行可能なコマンドに制限なし（ジョブズを信頼する設計）

## 対応する操作カテゴリ
- Pythonスクリプト実行（`python xxx.py`）
- パッケージ管理（`pip install xxx`）
- Git操作（`git add / commit / push`）
- バッチ/PowerShell実行（`xxx.bat`, `powershell xxx.ps1`）
- その他任意のWindowsコマンド全般

## 非対応（将来対応予定）
- 対話型コマンド（stdin待ちのプロセス）
- リアルタイムストリーミング出力
- 複数コマンドの並列実行
