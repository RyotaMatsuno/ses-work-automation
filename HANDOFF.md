# 引き継ぎメモ（次の会話でこのファイルを見せてください）

最終更新: 2026-04-28

---

## ジョブズへの運用指示

### 自走ルール
- 接続済みツールは確認を取らず自走して使う。送信系のみ最終確認
- CEOがやらないと進まない作業がある場合は、自動化する方法を毎回提案する
- ファイルが必要な場合はジョブズがチャット上に内容を貼る or ダウンロード可能な形で提供する（CEOに検索させない）
- 松野が行う作業は最低限に減らす。松野はClaudeとLINEだけで業務完結する
- PJ内ファイルの更新が必要な場合は、ses_work/project_files/に最新版を作成し、PJへの反映手順を提示する

---

## 今日のタスク（2026-04-28）

### 1. PCセットアップ ✅ 完了
- Python・Node.js・Git・Claude Desktop インストール済み
- Filesystem MCP・Notion MCP・Playwright MCP・ses-mail MCP 動作確認済み
- Gmail・Google Calendar・Google Drive・Claude in Chrome 接続済み
- タスクスケジューラ設定済み

### 2. 各機能連携確認 ⬜ 未実施
- Notion DB読み書きテスト
- ses-mailメール送受信テスト
- LINE Webhook動作テスト（松野公式・岡本公式）
- マッチングAI動作テスト

### 3. 自動マッチング構築確認 ⬜ 未実施
- 公式LINEから松野・岡本宛に案件送信→自動マッチング→提案文生成→メール送信の一気通貫テスト

### 4. メールログイン ⬜ 未実施
- ses-mail MCPでの松野・岡本アドレスのログイン確認

### 5. LINE PCアプリインストール ⬜ 未実施
- wingetで失敗。手動インストールが必要

---

## ✅ 完了済み全機能

### LINE Webhook v4（Railway稼働中）✅
- 松野用: /webhook
- 岡本用: /webhook_okamoto
- AI判定 → 人材/案件DB登録 → マッチング → 提案文ドラフト → LINE返信

### Outlook v3（複数アカウント対応・タスクスケジューラ稼働中）✅
- 複数アカウント対応済み
- 毎日9h/13h/18h自動実行
- **⚠️ 個人アドレスともう1つのアドレスを.envに追加する**

### メール送信MCP ✅
- Claude Desktop上でメール送信・受信確認が可能
- 松野アドレス（r-matsuno@terra-ltd.co.jp）
- 岡本アドレス（r-okamoto@terra-ltd.co.jp）

### Filesystem MCP ✅
- ses_work / Python_test / AppData全域にアクセス可能
- 設定ファイルの直接編集も可能

### ダブルチェック（岡本のClaude用）✅
- 岡本に完全マニュアル＋仕組み説明送付済み
- **岡本の制限解除待ち**

### Freee請求書自動生成 ⏳
- スクリプト・タスクスケジューラ登録済み
- **⚠️ APIキー取得・.env追記**

---

## 🔴 残りタスク

### タスク1: Outlookアカウント追加
`config/.env` に追記するだけ。スクリプト側は対応済み。

### タスク2: 岡本セットアップ（制限解除後）
1. 岡本に mail_mcp/mail_server.py を送る
2. 岡本から公式LINEの3点を受け取る → ✅ 受け取り済み・.env登録済み
3. 岡本のWebhook URL設定を岡本に依頼（/webhook_okamoto）

### タスク3: Freee APIキー取得・.env追記

---

## メール運用ルール

| アドレス | 担当 |
|---|---|
| r-matsuno@terra-ltd.co.jp | 松野 |
| r-okamoto@terra-ltd.co.jp | 岡本 |
| 共通アドレス（2つ） | 交互に割り振り（岡本2:松野1） |

---

## 接続済みツール全一覧

### ローカルMCP（Claude Desktop）
| ツール | 用途 | 自走 |
|---|---|---|
| Notion | エンジニアDB・案件DBの読み書き | ○ |
| Playwright | ブラウザ自動操作（PC側） | ○ |
| Filesystem | ローカルファイル読み書き | ○ |
| ses-mail | terraアドレスでのメール送受信 | ○（送信時のみCEO確認） |

### クラウド連携
| ツール | 用途 | 自走 |
|---|---|---|
| Google Calendar | 予定の確認・作成・削除 | ○ |
| Gmail | メール検索・スレッド閲覧・下書き作成 | ○ |
| Google Drive | ファイル検索・ダウンロード | ○ |
| Claude in Chrome | ブラウザ操作 | ○ |

---

## Notion DB
- エンジニアDB: 343450ff-37c0-819d-8769-fb0a8a4ceeb1
- 案件DB: 343450ff-37c0-81e4-934e-f25f90284a3c

## Railway
- URL: https://ses-work-automation-production.up.railway.app/webhook
- 岡本用: https://ses-work-automation-production.up.railway.app/webhook_okamoto

## 設定ファイルの場所
- claude_desktop_config.json: %LOCALAPPDATA%\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\
- 設定マスター: ses_work\config_source.json
- ※設定変更時は config_source.json を編集 → update_config.py をダブルクリック
- ※新PCではFilesystemのcommandが `C:\Users\ma_py\AppData\Roaming\npm\mcp-server-filesystem.cmd` に変更されている（npx.cmdではなく直接パス）

---

## 次のチャットでの始め方
「HANDOFF.mdを読んで続きをお願いします」でこのファイルをドラッグ&ドロップ
