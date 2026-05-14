# 完成済みインフラ サマリー

最終更新: 2026-05-13

---

## AI体制

### ジョブズ（経営参謀）
- 松野CEOの唯一の対話相手
- 経営判断・方針決定・テスラへの指示出し・SES営業マッチング担当
- Claude Desktop で稼働

### テスラ（インフラ担当）
- ジョブズ指揮下のシステム・インフラ専任AI
- 技術実装・環境整備・自動化開発を専任で担う
- Claude.ai 別プロジェクトとして作成済み（2026-05-12）
- 詳細仕様: `ses_work/project_files/TESLA_SPEC_v1.md`
- **インフラ系作業は全てテスラに委任する**

### テスラへの指示の出し方
1. ジョブズが「テスラへ: [タスク内容・要件・参照ファイル]」の形式で整理
2. 松野がテスラのチャットに貼り付け
3. テスラが実行・完了報告をジョブズ経由でCEOに届ける

---

## 完成済みの環境

### 1. ジョブズ コマンドサーバー（ターミナル完全自動化）

| ファイル | パス |
|---|---|
| HTTPサーバー本体 | `ses_work/local_server/command_server.py` |
| MCPブリッジ | `ses_work/local_server/mcp_bridge.py` |
| 自動起動バッチ | `ses_work/local_server/start_server.bat` |
| 仕様書 | `ses_work/local_server/SPEC.md` |

**仕様:**
- URL: `http://127.0.0.1:8765` / 認証: `X-Auth-Token: jobz-terra-2026`
- エンドポイント: `POST /run` / `POST /write_and_run` / `GET /health`
- 自動起動: Windowsスタートアップ登録済み

---

### 2. SESメール送受信（ses-mail）

- MCPサーバー: `ses_work/mail_mcp/mail_server.py`
- アカウント: `matsuno` / `okamoto` / `sessales`

---

### 3. LINE Webhook

| アカウント | URL | 状態 |
|---|---|---|
| 松野 | https://line-webhook-74735301292.asia-northeast1.run.app/webhook | ✅ 設定済み |
| 岡本 | https://line-webhook-74735301292.asia-northeast1.run.app/webhook_okamoto | ⏳ 岡本からアクセス許可待ち |

---

### 4. メール添付スキルシート自動取り込み（実装中）

- 場所: `ses_work/mail_attachment_importer/`
- 3点セット作成済み（CLAUDE.md / SPEC.md / TASKS.md）
- 実装はClaude Desktop再起動後にテスラへ委任

---

### 5. 接続済みMCPツール一覧

| ツール名 | 用途 | 状態 |
|---|---|---|
| notion | エンジニアDB・案件DB読み書き | ✅ 稼働中 |
| filesystem | ローカルファイル読み書き | ✅ 稼働中 |
| ses-mail | terraアドレスメール送受信 | ✅ 稼働中 |
| jobz-command | ターミナルコマンド自律実行 | ✅ 稼働中 |
| playwright | ブラウザ自動操作 | ✅ 稼働中 |
| Gmail | Gmailメール操作 | ✅ 接続済み |
| Google Calendar | 予定管理 | ✅ 接続済み |
| Google Drive | ファイル管理 | ✅ 接続済み |
| Claude in Chrome | ブラウザ操作 | ✅ 接続済み |

---

### 6. Notion DB

| DB名 | ID |
|---|---|
| エンジニアDB | 343450ff-37c0-819d-8769-fb0a8a4ceeb1 |
| 案件DB | 343450ff-37c0-81e4-934e-f25f90284a3c |

---

## 開発ルール（全PJに適用）

### 3点セット必須運用

| ファイル | 役割 | 作成タイミング |
|---|---|---|
| `CLAUDE.md` | 作業ルール・禁止事項（200行以内） | 実装開始前に必ず作成 |
| `SPEC.md` | 仕様書 | CLAUDE.mdの次に作成 |
| `TASKS.md` | 実装チェックリスト | SPEC.mdの次に作成 |

### 実装開始の流れ
1. ジョブズがCLAUDE.md → SPEC.md → TASKS.md を作成
2. テスラに「この3点を使って実装して」と依頼
3. テスラがTASKS.md順に実装・完了ごとに更新
