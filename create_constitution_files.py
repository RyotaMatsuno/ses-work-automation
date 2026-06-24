# -*- coding: utf-8 -*-
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_FILES = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\project_files"

constitution = """# ジョブズ行動憲法 v1
最終更新: 2026-06-15

## 【核心3原則】
1. 実装はCursorに投げる。ジョブズはコードを書かない。
2. 送信系（メール/LINE/公開投稿）は必ず松野確認を取る。
3. CostGuardなしでLLMを呼び出さない。

## 【自走ルール】
4. jobz-commandが応答すればツールを確認なく使う（Notion/Gmail/Drive/Playwright）
5. Cursor作業指示はpending_tasks/に保存→松野はCursorを開くだけ
6. 週末はOpus調査のみ。実装・送信・DB更新・請求確定は平日のみ。
7. ファイルはジョブズがチャットに貼る。松野に検索させない。

## 【エスカレーション】
8. 同じエラーで2回失敗→wall_hitting.py（GPT/Gemini壁打ち）→それでも解決しなければ松野へ
9. 費用発生・岡本連絡・根本設計変更→必ず松野確認
10. gate_checker NG→技術的NGは壁打ち自走、仕様NGは松野確認

## 【モデル選択】
11. デフォルト: Sonnet 4.6
12. Opus 4.8: 法人化・契約判断・複雑アーキ設計（月5〜10回）
13. チャット冒頭1行目に宣言する

## 【技術制約サマリー】
14. jobz-command: localhost:8765 / token:jobz-terra-2026 / 27分超はハング
15. Notion: MCPクエリ不可→direct REST / Notion-Version:2022-06-28
16. freee: /iv/invoices エンドポイント / 確定は松野手動
17. 日本語パス(デスクトップ)をcwd/コマンドに直接渡さない
18. PowerShell &&チェーン不可 / grep→rg / taskkill /im python.exe禁止

## 【事業コンテキスト】
19. TERRA粗利80% / FT階段契約68%（現在9件・あと2件で75%）
20. 松野LINE user_id: Ue3508b43b84991f5a68281da5bf4cf39
21. 岡本LINE user_id: Uac1d23408573586affa37577c4e2b2ab
22. 通知は松野公式LINEチャンネルから送信のみ / 月200通上限（上限前提で設計）

## 【開発ルール】
23. 3点セット必須: CLAUDE.md→SPEC.md→TASKS.md→実装
24. ゲート①: SPEC完成後GPT-4oレビュー / ゲート②: 実装後GPT-4oレビュー
25. コスト状態正本: AppData/Local/ses_work_state/cost_state.json
26. 引き継ぎ: 20ラリーでジョブズから宣言→次チャット用メッセージ自動生成

## 【詰まったら参照】
27. ハマりパターン辞書v1.md（jobz/Notion/freee/Cursor別の既知問題）
28. CEO指示書v10.md（方針・長期ビジョン）
29. INFRA_SUMMARY.md（現在のシステム状態）

## 【禁止事項】
30. バックログ確認前に「未着手」と決めつける / 環境確認せずjobz不可と決めつける
"""

hamari = """# ハマりパターン辞書 v1
最終更新: 2026-06-15
用途: 詰まったときだけ参照。jobz/Notion/freee/Cursor/Windows/LINE別の既知問題集。

---

## jobz-command

| 症状 | 原因 | 対処 |
|---|---|---|
| WinError 10061 接続拒否 | command_server.pyが未起動 | start_server.bat実行。watchdog.logでループ確認 |
| pythonw起動でサーバーが即死 | importするモジュールのモジュールレベルにtry/exceptなしのsys.stdout.reconfigure | 該当ファイルをtry/exceptで囲む or common/io_utils.pyのsetup_stdout()を使う |
| timeout 27分超 | jobz-command設計上限 | Windowsターミナルで直接実行 |
| taskkill /im python.exe | jobz-commandサーバー自身を殺す | タスクマネージャで対象PIDのみkill |
| PowerShell &&チェーン失敗 | &&はcmd専用 | コマンドを分けて実行 |
| $変数がPowerShell文字列内で展開 | PowerShellの$解釈 | heredocまたはスクリプトファイル化 |
| grep: コマンドが見つかりません | Windowsにgrepなし | rg (ripgrep)を使う |
| 日本語パスでサイレント失敗 | cwd=日本語パスが化ける | Unicode escapeまたは絶対パスで指定 |

## Notion API

| 症状 | 原因 | 対処 |
|---|---|---|
| invalid_request_url (400) | notion:API-query-data-sourceが未対応 | direct REST: POST /v1/databases/{id}/query |
| プロパティ名エラー | 日本語プロパティ名の誤り | 案件詳細/必要スキル等は完全一致必須 |
| フィルターtype不一致 | DBのプロパティ型を先にGETで確認していない | /v1/databases/{id}でスキーマ確認してからフィルタ構築 |
| Notion-Versionヘッダー必須 | 未指定でエラー | Notion-Version: 2022-06-28 を必ず付与 |

## freee

| 症状 | 原因 | 対処 |
|---|---|---|
| 404 /api/1/invoices | 旧エンドポイント廃止 | /iv/invoices を使う |
| unit validation error | unitが空文字 | unit="式" 等1文字以上必須 |
| unit_price型エラー | 数値型で送っている | 文字列型で送る |
| PUT bodyでエラー | {invoice:{}}ラッパーを使っている | トップレベルbody形式、company_idをbodyに |
| 源泉徴収の計算誤り | 全社同一処理 | TERRA=税抜×10.21% / GL・FT=源泉なし |

## Cursor / Python実装

| 症状 | 原因 | 対処 |
|---|---|---|
| OneDriveでWinError 5 | 同期ロックでatomic rename失敗 | state系ファイルはAppData/Local配下に置く |
| cost_state.jsonが複数存在 | OneDrive配下はorphan | OneDrive配下を削除。AppData正本1本に統一 |
| sys.stdout.reconfigureでAttributeError | pythonwではstdout=None | common/io_utils.pyのsetup_stdout()を使う |
| subprocess Popenで日本語パスが化ける | shell=Trueの文字列結合 | リスト形式で渡す or Unicode escape |
| matching_v2 JSONDecodeError | max_tokens不足で出力が切れる | max_tokensを8000以上に（2026-06-15修正済み） |
| gspread書き込み失敗 | サービスアカウントはPersonal Drive quota無し | OAuth2 credentials (token_sheets.json)を使う |

## LINE

| 症状 | 原因 | 対処 |
|---|---|---|
| push 429（月次上限） | 月200通フリープラン上限到達 | push_or_log()を使う。「作業進捗」とLINEに打つとreplyで状態確認可 |
| 月末に毎回429 | 200通は設計の前提として扱う | LINE残通数を毎push前に確認する設計（006タスク実装済み） |
| gate_checkerのLINE通知429 | 同上 | gate_check.pyの通知関数が残通数チェック付きに修正済み |
| 岡本へのpush失敗 | 松野チャンネルから送るべき | 送信は松野公式LINEチャンネルのみ |
| 「進捗」でマッチング結果が返ってくる | 即時ワード判定と衝突 | 「作業進捗」「案件進捗」「人員進捗」の完全一致コマンドに変更（006/007タスク） |

## Cloud Run / デプロイ

| 症状 | 原因 | 対処 |
|---|---|---|
| --set-env-varsで既存変数が消える | 上書きモード | --update-env-vars を使う |
| デプロイ後も古いコードが動く | イメージキャッシュ | --no-cache オプション付きでdeploy |

## Google Sheets / Drive

| 症状 | 原因 | 対処 |
|---|---|---|
| token_uri エラー | サービスアカウントJSONの形式問題 | OAuth2 credentials (token_sheets.json)を使う |
| ws.update()で引数エラー | 古いgspread API | ws.update(range_name='A1', values=[['value']])の形式を使う |
"""

for filename, content in [
    ("ジョブズ行動憲法v1.md", constitution),
    ("ハマりパターン辞書v1.md", hamari),
]:
    path = os.path.join(PROJECT_FILES, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"作成: {path}")

print("\n--- project_files/ 現在のファイル ---")
for f in sorted(os.listdir(PROJECT_FILES)):
    print(f"  {f}")
