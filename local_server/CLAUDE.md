# CLAUDE.md — ジョブズ コマンドサーバー 作業ルール

## プロジェクト概要
Claude Desktop（ジョブズ）がローカルPCで任意のコマンドを自律実行するためのHTTPサーバー + MCPブリッジ。

## 技術スタック
- Python 3.x（標準ライブラリのみ。外部ライブラリはmcpのみ許可）
- HTTP: `http.server`（標準ライブラリ）
- MCP: `mcp` ライブラリ（stdio_server）
- 対象OS: Windows 11

## ファイル構成
```
local_server/
  command_server.py   # HTTPサーバー本体（localhost:8765）
  mcp_bridge.py       # Claude Desktop用MCPブリッジ
  start_server.bat    # スタートアップ起動用
  server.log          # 実行ログ（自動生成）
  CLAUDE.md           # 本ファイル
  SPEC.md             # 仕様書
  TASKS.md            # 実装チェックリスト
```

## AI使用ルール（必須）
1. **設計フェーズ: Opusモデル / effort=max / Planモード**
   - いきなりコードを書かせない
   - まずPlanモードで設計図・実装方針を固める
   - 設計はケチらず最高性能で
2. **実装フェーズ: Sonnetモデル / effort=medium**
   - 設計が固まってから実装に入る
   - 速さ重視・手数で勝負

## 作業ルール
1. **機能追加は SPEC.md に定義されたものだけ実装する**。勝手に機能を追加しない。
2. **1タスクずつ実装し、TASKS.md のチェックを更新してから次へ進む**。
3. **外部ライブラリを勝手に追加しない**。追加が必要な場合は必ず確認する。
4. **セキュリティ設定（AUTH_TOKEN・localhost制限）は絶対に緩めない**。
5. **既存の動作を壊す変更をする前は必ず確認する**。
6. **ログは必ずserver.logに書く**。printだけで終わらせない。
7. コメントは日本語で書く。

## 禁止事項
- 0.0.0.0バインド（外部公開）への変更
- AUTH_TOKENの削除・ハードコード以外の保存
- 不要なエンドポイントの追加
- asyncio化・フレームワーク化（FastAPI等）への勝手な移行
- テストコードの本体への混入
- Planモードをスキップしていきなりコードを書くこと

## 参照すべき設計書
- SPEC.md（何を作るかの定義）
- TASKS.md（実装順序）
- ../claude_desktop_config.json（MCP登録状況）
