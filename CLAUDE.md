# CLAUDE.md — TERRA SES ジョブズ作業ルール（Cursor用）

最終更新: 2026-06-09

---

## このファイルの目的

CursorのComposerがこのリポジトリで作業する際に必要な文脈・ルール・禁止事項を全て記載する。
作業前に必ず全文を読むこと。

---

## 事業基本情報

- 事業主: 松野（CEO）/ 再委託パートナー: 岡本
- 業種: SES（システムエンジニアリングサービス）人材派遣
- 契約先: 株式会社TERRA（粗利80%）/ フラップテック（粗利68%）/ グレイスライン（粗利60%）
- 稼働エンジニア: 15名弱
- 目標: 2027年上期に法人化

---

## AI体制（役割分担）

| 役割 | ツール | 担当範囲 |
|---|---|---|
| ジョブズ（経営参謀） | Claude.ai | 設計・判断・SPEC作成・Cursorへの指示書生成 |
| Cursor実装 | Cursor + Sonnet 4.6 | コード実装・修正・バグ修正 |
| ジラード（営業AI） | .claude/agents/girard.md | 提案文ドラフト（draft-only） |
| 渋沢（経理AI） | .claude/agents/shibusawa.md | freee・契約マスター（draft-only） |
| ダブルチェック | GPT-4o API直叩き | ゲート②コードレビュー |

**Cursorは実装専任。設計・判断はジョブズ（Claude.ai）が行う。**

---

## 作業環境

- 作業ディレクトリ: `C:\Users\ma_py\OneDrive\デスクトップ\ses_work`
- GitHub: `RyotaMatsuno/ses-work-automation`
- jobz-command: `http://127.0.0.1:8765` / token: `jobz-terra-2026`
- 環境変数: `ses_work/config/.env`（全APIキー・DB ID格納）
- Cloud Run: `line-webhook` / asia-northeast1

---

## 情報のSSoT（Single Source of Truth）

| 情報種別 | 正解の場所 |
|---|---|
| エンジニア情報 | Notion エンジニアDB `343450ff-37c0-819d-8769-fb0a8a4ceeb1` |
| 案件情報 | Notion 案件DB `343450ff-37c0-81e4-934e-f25f90284a3c` |
| AI作業キュー | Notion `37a450ff-37c0-819a-981b-c2e06ed282bb` |
| 契約・請求 | Google Sheets 契約マスター `1ORBtxtGqLAwv3YU8CGeLX7gWFgvKOivMTCZZiWtYGfI` |
| 事業ルール | `line_bridge/SPEC.md` / `判断マニュアルv3.md` |
| インフラ状態 | `INFRA_SUMMARY.md` |

---

## 開発ルール（必須）

### 3点セット
新機能・新システムは必ずこの順で作る。実装はその後。

1. `CLAUDE.md`（作業ルール・禁止事項）
2. `SPEC.md`（仕様書）
3. `TASKS.md`（実装チェックリスト）

### ゲート制度
- **ゲート①**: SPEC完成後にGPT-4oで設計レビュー → GO判定後に実装開始
- **ゲート②**: 実装完了後にGPT-4oでコードレビュー → GO判定後にデプロイ
- レビュアーは実装者と**別個体**（実装=Sonnet 4.6、レビュー=GPT-4o）

### エンコーディング（Windows必須）
- ファイル書き込みは必ずUTF-8
- 日本語パス（`デスクトップ`）をcwd/コマンドに直接渡さない
- スクリプト冒頭に `sys.stdout.reconfigure(encoding='utf-8', errors='replace')`
- `python -c` は改行不可。複数行はスクリプトファイル化して実行

### jobz-command制約
- `run_command` + `write_and_run` のみ使用
- 27分超の処理はハングする → 長時間バッチはWindowsターミナルで直接実行
- Notionの大量操作はMCPではなくPython REST API直叩き

---

## CostGuard（必須）

**全LLM呼び出しにCostGuardを通すこと。**

- 制限値: $8/日・$140/月（`config/.env` の `COST_DAILY_LIMIT` / `COST_MONTHLY_LIMIT`）
- LLM_KILL=1 で即時停止
- 6/2のコスト暴走（$50.88/日）の教訓。絶対に省略しない

---

## 禁止事項

- **松野にファイルを検索・ダウンロードさせる**
- **CostGuardなしでLLMを呼び出す**
- **3点セット（CLAUDE.md/SPEC.md/TASKS.md）なしで実装を開始する**
- **ゲート①②なしでCloud Runにデプロイする**
- **draft-only制約（ジラード・渋沢）を破って送信・確定操作をする**
- **freee請求書の確定・削除を自律実行する**（松野がfreee UIで操作）
- **本番Notion DBを無確認で大量書き込みする**
- **GitHubにAPIキー・シークレットをコミットする**
- **日本語パスをcwdに直接渡す**

---

## 人間確認ゲート（松野承認が必要）

以下は自律実行禁止。必ず松野にLINEまたはClaude.aiで確認を取る。

- Gmailでのメール送信
- freee請求書の確定・送信
- Notion本番DB（エンジニア・案件）の大量更新・削除
- Cloud Runデプロイ
- 契約マスターの書き込み

---

## Cursor作業指示の受け取り方

Claude.aiのジョブズが以下フォーマットで指示書を生成する。
Cursorはこの指示書に従って実装する。

```
【Cursor作業指示】
対象ディレクトリ: ses_work/xxx/
作業内容: ○○
参照ファイル: SPEC.md / TASKS.md / CLAUDE.md
完了条件: ○○
質問がある場合: Claude.aiチャットに貼り付けて確認
```

---

## 完成済みシステム一覧

| システム | パス | 状態 |
|---|---|---|
| jobz-commandサーバー | `local_server/` | ✅ 稼働中 |
| mail_pipeline | `mail_pipeline.py` | ✅ v4.1稼働中 |
| matching_v3 | `matching_v3/` | ✅ 稼働中（staleness bugあり） |
| LINE Webhook | `line_webhook/` | ✅ Cloud Run稼働中 |
| LINE bridge + AI作業キュー | `line_webhook/line_bridge.py` | ✅ 2026-06-09デプロイ済み |
| freee請求書自動化 | `freee/` | ✅ 毎月1日09:00自動実行 |
| ジラード/渋沢サブエージェント | `.claude/agents/` | ✅ 配置済み |

---

## 変更履歴

| 日付 | 変更内容 |
|---|---|
| 2026-05-19 | v1初版 |
| 2026-06-09 | v2全面刷新。Cursor移行対応。CEO指示書v8・INFRA_SUMMARY最新版を反映。AI作業キュー・LINE bridge追加。 |
