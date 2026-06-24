# 完成済みインフラ サマリー

最終更新: 2026-06-10

## AI体制（確定版）

### ジョブズ（経営参謀）

- 松野CEOの唯一の対話相手

- 経営判断・方針決定・SPEC.md設計・Cursorへの指示書生成

- **Claude.ai ブラウザ版で稼働（2026-06-09 Desktop→ブラウザ移行完了）**

### Cursor（コード実装専任）

- ジョブズが生成した【Cursor作業指示】をもとにコードを実装

- ses_workフォルダをCursorで開いてComposerに貼り付けて使用

- CLAUDE.mdを自動参照して事業文脈を把握

- **Codexから完全移行済み（2026-06-09）。ChatGPT Plus解約完了**

### ダブルチェック（GPT-4o）

- ゲート①（設計レビュー）・ゲート②（コードレビュー）で使用

- API直叩き。実装者（Sonnet 4.6）と別個体を維持

### タスク分担

| **タスク種別** | **担当** |
| --- | --- |
| 経営判断・方針・設計 | ジョブズ |
| 【Cursor作業指示】生成 | ジョブズ |
| Notion/メール/DB操作 | ジョブズ |
| Pythonスクリプト実装・修正 | Cursor |
| HTML/CSS/JS/Playwright | Cursor |
| バッチ処理・ファイル変換 | Cursor |
| 設計レビュー・コードレビュー | GPT-4o |

## 完成済みの環境

### 1. ジョブズ コマンドサーバー（ターミナル完全自動化）

| **ファイル** | **パス** |
| --- | --- |
| HTTPサーバー本体 | ses_work/local_server/command_server.py |
| MCPブリッジ | ses_work/local_server/mcp_bridge.py |
| 自動起動バッチ | ses_work/local_server/start_server.bat |

**仕様:**

- URL: http://127.0.0.1:8765 / 認証: X-Auth-Token: jobz-terra-2026

- エンドポイント: POST /run / POST /write_and_run

- 自動起動: Windowsスタートアップ登録済み

**制約:**

- 27分超の処理はサーバーがハング → 長時間バッチはWindowsターミナルで直接実行

- Notionの大量操作はMCPではなくjobz-command経由でPython REST APIを直叩く

### 2. Cursor（コード実装環境）

| **項目** | **内容** |
| --- | --- |
| バージョン | Free Plan（APIキー直挿しのためプラン制限なし） |
| モデル | claude-sonnet-4-6（AnthropicAPIキー直挿し） |
| 作業フォルダ | C:\Users\ma_py\OneDrive\デスクトップ\ses_work |
| 設定ファイル | ses_work/CLAUDE.md（2026-06-09 v2刷新済み） |
| 並列実行 | Composerタブを複数開いて並列実装可能 |
| 旧Codex | **廃止。ChatGPT Plus $20/月解約完了** |

### 3. SESメール送受信（ses-mail）

- MCPサーバー: ses_work/mail_mcp/mail_server.py
- RESTサーバー: ses_work/mail_mcp/mail_rest.py（2026-06-10 稼働中）

- アカウント: matsuno / okamoto / sessales

- **Claude.aiブラウザからはIMAP接続不可（ファイアウォールブロック）。jobz-command経由のみ動作**

### 4. LINE Webhook + LINE Bridge（2026-06-09 大幅更新）

| **アカウント** | **URL** | **状態** |
| --- | --- | --- |
| 松野 | https://line-webhook-74735301292.asia-northeast1.run.app/webhook | ✅ 設定済み |
| 岡本 | https://line-webhook-74735301292.asia-northeast1.run.app/webhook_okamoto | ⏳ 岡本からアクセス許可待ち |

**LINE Bridge（2026-06-09新設）:**

- line_webhook/line_bridge.py

- ルーター: LINEメッセージを即時系/営業重作業/経理/開発/要確認に振り分け

- 引き継ぎメッセージパーサー（B方式）: ■セクションを自動抽出してNotionキューに登録

- 並列処理: ThreadPoolExecutor(max_workers=5)で全タスクを並列実行

- Cloud Scheduler: 5分おきに自動起動（line-bridge-worker-cron）

- revision: line-webhook-00065-4h9 / max-instances=5 / timeout=120s

**AI作業キューDB:**

- Notion DB ID: 37a450ff-37c0-819a-981b-c2e06ed282bb

- スキーマ: task_id / 受付元 / 種別 / 優先度 / 締切 / 入力データ / 使用許可 / 担当 / 状態 / コスト見込み / 結果リンク / 人間確認 / 作成日時 / 完了日時

- 担当enum: matching_v3 / jobz / girard / shibusawa / cursor / claude-code / codex

- 状態: queued → running → review（人間確認要）/ done / blocked

- 自動失効: done/blocked を7日後にアーカイブ（cron週次）

- ⚠️ **NotionMCP新API（data_source方式）ではクエリ不可（invalid_request_url）。ブラウザ環境でのキュー監視はjobz-command経由Pythonスクリプトを使用すること**

**LINE運用ルール（2026-05-22確定）:**

- 松野・岡本への通知は**松野公式LINEチャンネルのみ**から送信

- 岡本公式LINEは「提案ナレッジ蓄積専用」

- LINE Messaging APIフリープランは月200通上限。push節約設計済み

- pushカウンター: 月次残150通を下回ったらreply-only modeに自動切替

### 5. mail_pipeline.py

| **項目** | **内容** |
| --- | --- |
| バージョン | v4.1 |
| パス | ses_work/mail_pipeline.py |
| 実行間隔 | Windowsタスクスケジューラ30分おき |
| モデル | gpt-4.1-nano（コスト最適化済み） |
| ⚠️ 既知問題 | 取込時バリデーション未実装（P1〜P6の品質チェックなし）→ db_quality_fixフェーズ2で対応予定 |

### 6. matching_v3（AIマッチングエンジン）

| **項目** | **内容** |
| --- | --- |
| パス | ses_work/matching_v3/ |
| 方式 | ルールベース（LLMゼロ）でマッチング判定 |
| LLM使用 | gpt-4.1-nano（メール文面生成のみ） |
| バグ修正状況 | **全バグ修正済み（2026-06-10時点）** |
| 実行 | 平日8:00自動実行（weekday_guard.py） |
| ⚠️ 鮮度判定 | `last_edited_time` 基準は設計上の問題あり（一括メンテで全員新鮮扱い）。`情報取得日` フィールドへの移行はフェーズ2で対応 |

### 7. freee請求書自動化

| **項目** | **内容** |
| --- | --- |
| メインスクリプト | ses_work/freee/freee_invoice_v2.py |
| 廃止スクリプト | freee_invoice_monthly.py（2026-06-19退役・起動時即終了。v2一本化） |
| スケジューラ | 毎月1日09:00自動実行（SES_Freee_Invoice / freee_auto_invoice） |
| ソース | 契約マスター Google Sheets（SSoT） |
| 注意 | freee請求書の確定・削除は**松野がfreee UIで手動操作**（自律実行禁止） |

### 8. mail_attachment_importer

| **項目** | **内容** |
| --- | --- |
| パス | ses_work/mail_attachment_importer/ |
| 状態 | **Phase9完了・稼働中（2026-06-10）** |
| 対応形式 | A=添付Excel/PDF/Word / B=Google SpreadsheetURL(1人) / C=Google SpreadsheetURL(複数人) |

### 9. ジラード / 渋沢 サブエージェント

| **エージェント** | **ファイル** | **役割** |
| --- | --- | --- |
| ジラード | .claude/agents/girard.md | 営業専任。提案文ドラフト（draft-only） |
| 渋沢 | .claude/agents/shibusawa.md | 経理専任。freee・契約マスター（draft-only） |

- **draft-only厳守**: 送信・DB更新・請求確定は一切しない

- _validate_draft()で「送信しました/確定しました」等の実行宣言を自動検知してblocked

- 粗利フロア: 松野¥50,000 / 岡本¥30,000（ジラードの静的ルール）

### 10. gate_checker（GPT-4oゲート）

| **項目** | **内容** |
| --- | --- |
| パス | ses_work/gate_checker/ |
| 状態 | **完成・稼働中（2026-06-10）** |
| 実行 | `python gate_checker/gate_check.py --phase [requirements\|implementation] --file [対象ファイル]` |

### 11. db_quality_fix（エンジニアDBクレンジング）NEW

| **項目** | **内容** |
| --- | --- |
| パス | ses_work/db_quality_fix/ |
| 状態 | **SPEC完成・Cursor実装待ち（2026-06-10）** |
| 目的 | 外国籍違反・プレースホルダ名・案件メール混入等7パターンの検出と修正 |
| 参照 | ses_work/db_quality_fix/SPEC.md |

### 12. 接続済みMCPツール一覧

| **ツール名** | **用途** | **状態** |
| --- | --- | --- |
| notion | エンジニアDB・案件DB・AI作業キュー読み書き | ✅ 稼働中（DB query APIはdata_source方式が不可。databases/{id}/queryを使うこと） |
| filesystem | ローカルファイル読み書き | ✅ 稼働中 |
| ses-mail | terraアドレスメール送受信 | ✅ 稼働中（jobz-command経由のみ） |
| jobz-command | ターミナルコマンド自律実行 | ✅ 稼働中（ブラウザ版では接続要確認） |
| playwright | ブラウザ自動操作 | ✅ 稼働中 |
| Gmail | Gmailメール操作 | ✅ 接続済み |
| Google Calendar | 予定管理 | ✅ 接続済み |
| Google Drive | ファイル管理 | ✅ 接続済み |
| Claude in Chrome | ブラウザ操作 | ✅ 接続済み |

### 13. Notion DB

| **DB名** | **ID** |
| --- | --- |
| エンジニアDB | 343450ff-37c0-819d-8769-fb0a8a4ceeb1 |
| 案件DB | 343450ff-37c0-81e4-934e-f25f90284a3c |
| AI作業キューDB | 37a450ff-37c0-819a-981b-c2e06ed282bb |
| SESナレッジWikiページ | 353450ff-37c0-8145-9e3e-d80c8c8ed594 |

## 未完了タスク（引き継ぎ）

| **タスク** | **状態** | **対応方法** |
| --- | --- | --- |
| db_quality_fix cleaner.py実装 | **🔴 最優先・Cursor待ち** | ses_work/db_quality_fix/CURSOR_INSTRUCTION.md をCursorに投げる |
| mail_pipeline バリデーション強化（フェーズ2） | 未着手 | db_quality_fix完了後にジョブズがSPEC作成 |
| 鮮度判定フィールド移行（情報取得日） | 未着手 | mail_pipelineフェーズ2と同時に対応 |
| 岡本LINE Webhook疎通確認 | 岡本設定待ち | 岡本からURL受領後にジョブズが反映 |
| ChatGPT Plus解約 | **✅ 完了** | Codex廃止のため解約済み |

## 開発ルール（全PJに適用）

### 3点セット必須運用

| **ファイル** | **役割** | **作成タイミング** |
| --- | --- | --- |
| CLAUDE.md | 作業ルール・禁止事項（200行以内） | 実装開始前に必ず作成 |
| SPEC.md | 仕様書 | CLAUDE.mdの次に作成 |
| TASKS.md | 実装チェックリスト | SPEC.mdの次に作成 |

### ゲート制度

- ゲート①: SPEC完成後にGPT-4oで設計レビュー → GO後に実装

- ゲート②: 実装完了後にGPT-4oでコードレビュー → GO後にデプロイ

- レビュアーは実装者と**別個体**（Sonnet 4.6 vs GPT-4o）

### CostGuard（必須）

- 全LLM呼び出しにCostGuardを通す

- 制限値: $8/日・$140/月（config/.envのCOST_DAILY_LIMIT/COST_MONTHLY_LIMIT）

- LLM_KILL=1で即時停止

- 6/2のコスト暴走（$50.88/日）の教訓。絶対に省略しない

### エンコーディング（Windows必須）

- ファイル書き込みは必ずUTF-8

- 日本語パス（デスクトップ）をcwd/コマンドに直接渡さない

- スクリプト冒頭に sys.stdout.reconfigure(encoding='utf-8', errors='replace')
