# 引き継ぎメモ（次の会話でこのファイルを見せてください）

最終更新: 2026-04-23

---

## ✅ 完了済み全機能

### LINE Webhook v3（Railway）
- Claude AIでメッセージを自動判定（人材 or 案件）
- 人材情報 → エンジニアDB自動登録 → LINE返信
- 案件情報 → 案件DB自動登録 → マッチングAI → 提案文ドラフト → LINE返信
- ダブルチェックは岡本のClaude Codeで実施（分離済み）
- **⚠️ git pushがまだ → Railway未反映**

### Outlook v2（ローカル・タスクスケジューラ済み）
- Claude AIでメール内容を自動判定
- 人材メール → エンジニアDB / 案件メール → 案件DB
- 毎日9h/13h/18h自動実行 ✅

### ダブルチェック（岡本のClaude Code用）
- `double_check/double_check.py` 作成済み
- `double_check/岡本用_ClaudeCode指示書.md` 作成済み
- 岡本がClaude Codeに指示書を貼り付けるだけで使える

### Freee請求書自動生成
- `freee/freee_invoice.py` 作成済み
- タスクスケジューラ登録済み（毎月25日AM10時）
- **⚠️ .envにFREEE_ACCESS_TOKEN / FREEE_COMPANY_IDを追加する必要あり**

### タスクスケジューラ（全登録済み）
- SES_Outlook_9h / 13h / 18h ✅
- SES_Freee_Invoice ✅

### LINE Webhook設定
- URL設定・Webhookオン ✅

---

## 🔴 次回やること（残タスク）

| 優先 | 作業 | 方法 |
|---|---|---|
| **1** | **git pushしてRailwayにデプロイ** | `ses_work\git_push.bat` をダブルクリック |
| **2** | **岡本にClaudeCode指示書を渡す** | `double_check\岡本用_ClaudeCode指示書.md` をLINEで送る |
| **3** | **FreeeのAPIキー取得・.env追記** | freeeメンテ終了後 |
| 4 | 岡本の公式LINEアカウント開設 | 手順書作成済み待ち |
| 5 | Notionに岡本共有ナレッジページ作成 | Notion MCP経由でジョブズが作成可能 |
| 6 | matching.pyの強化（既存の手動版） | 並行スコア対応 |

---

## Railwayデプロイ手順

`ses_work\git_push.bat` をダブルクリックするだけ。
→「Push complete」と表示されたら2〜3分でRailwayに自動反映。

---

## Freee APIキー取得手順

1. https://secure.freee.co.jp にログイン
2. 右上メニュー →「アプリ連携」→「個人アクセストークン」→ 発行
3. URLの `company_id=xxxxx` の数字も控える
4. `config/.env` に追記:
   ```
   FREEE_ACCESS_TOKEN=発行したトークン
   FREEE_COMPANY_ID=数字
   ```

---

## 実装済みフロー

### 松野/岡本の日常業務フロー（完成形）
```
①案件情報をLINEに送る（自由フォーマットでOK）
  ↓
②自動で案件DB登録 + マッチング + 提案文ドラフト生成
  ↓
③LINEに候補者リスト + 提案文ドラフトが返ってくる
  ↓
④岡本がClaude Codeに提案文を貼り付けてダブルチェック
  ↓
⑤修正済み提案文を確認 → 個人LINEで所属に送信
```

### Outlookからの自動登録（バックグラウンド）
```
毎日9時/13時/18時にメールをチェック
→ AIが人材/案件を自動判定
→ 各DBに自動登録
```

---

## システム構成
```
LINE受信 → Railway Webhook(v3) → AI判定 → DB登録 → マッチング → LINE返信
Outlook → outlook_to_notion.py(v2) → AI判定 → DB登録（毎日3回）
Notionエンジニアdb(稼働中) → freee_invoice.py → Freee請求書ドラフト（毎月25日）
岡本のClaude Code → ダブルチェックAI → 提案文修正
```

## Notion DB
- エンジニアDB: 343450ff-37c0-819d-8769-fb0a8a4ceeb1
- 案件DB: 343450ff-37c0-81e4-934e-f25f90284a3c

## Railway
- URL: https://ses-work-automation-production.up.railway.app/webhook
- ステータス: Online（git push後に新機能反映）

## GitHub
- リポジトリ: https://github.com/RyotaMatsuno/ses-work-automation

---

## 重要ファイル一覧

| ファイル | 役割 | 状態 |
|---|---|---|
| `git_push.bat` | Railway反映用git push | ⚠️ 未実行 |
| `config/.env` | 全APIキー | ✅（FreeeキーはまだNG） |
| `outlook/outlook_to_notion.py` | Outlook→Notion AI振り分け | ✅ 稼働中 |
| `line_webhook/webhook_server.py` | LINE Webhook AI全自動 | ✅ git push待ち |
| `double_check/double_check.py` | ダブルチェックAI（CLI版） | ✅ |
| `double_check/岡本用_ClaudeCode指示書.md` | 岡本へ渡す指示書 | ✅ 岡本に送付待ち |
| `freee/freee_invoice.py` | Freee請求書自動生成 | ✅ APIキー待ち |
| `setup_tasks.ps1` | タスクスケジューラ登録 | ✅ 実行済み |

---

## 次のチャットでの始め方
「HANDOFF.mdを読んで続きをお願いします」でこのファイルをドラッグ&ドロップ
