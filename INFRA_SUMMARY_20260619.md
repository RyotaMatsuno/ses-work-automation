# 完成済みインフラ サマリー

最終更新: 2026-06-19

## AI体制（確定版）

### ジョブズ（経営参謀）
- 松野CEOの唯一の対話相手
- 経営判断・方針決定・SPEC.md設計・Cursorへの指示書生成
- Claude.ai ブラウザ版で稼働

### Cursor（コード実装専任）
- ジョブズが生成した【Cursor作業指示】をもとにコードを実装
- ses_workフォルダをCursorで開いてComposerに貼り付けて使用
- CLAUDE.mdを自動参照して事業文脈を把握
- Codexから完全移行済み / ChatGPT Plus解約済み
- Cursor Pro $20/月

### ダブルチェック
- GPT-4o + Claude Sonnet 4.6 並列レビュー（2026-06-19 Task M完了）
- ゲート①（設計レビュー）・ゲート②（コードレビュー）で使用
- gate_checker/gate_check.py で自動実行

### タスク分担
| タスク種別 | 担当 |
|---|---|
| 経営判断・方針・設計 | ジョブズ |
| 【Cursor作業指示】生成 | ジョブズ |
| Notion/メール/DB操作 | ジョブズ |
| GPT壁打ち | ジョブズ（GPT-5.4 API） |
| Pythonスクリプト実装・修正 | Cursor |
| HTML/CSS/JS/Playwright | Cursor |
| 設計レビュー・コードレビュー | GPT-4o + Sonnet |

## 完成済みの環境

### 1. ジョブズ コマンドサーバー（ターミナル完全自動化）
- URL: http://127.0.0.1:8765 / 認証: X-Auth-Token: jobz-terra-2026
- エンドポイント: POST /run / POST /write_and_run
- 自動起動: Windowsスタートアップ登録済み
- 制約: 27分超の処理はサーバーがハング

### 2. Cursor（コード実装環境）
- Cursor Pro $20/月
- モデル: claude-sonnet-4-6（AnthropicAPIキー直挿し）
- 作業フォルダ: ses_work
- CLAUDE.md自動参照

### 3. mail_pipeline v6.0（2026-06-19 大幅更新）
| 項目 | 内容 |
|---|---|
| パス | ses_work/mail_pipeline/mail_pipeline.py (2077行) |
| 実行間隔 | Windowsタスクスケジューラ毎時 |
| モデル | gpt-4.1-nano（分類・抽出） |
| DB | raw_inbox.db (SQLite WAL) |
| v6.0変更点 | DB work queue統合（IMAP + DBバックログ再処理） |
| 分類方式 | ルールベース(analyze_final.py) + AI Batch(gpt-4.1-nano) |
| PROCESS_LIMIT | 200 |
| FETCH_LIMIT | 200 |

#### mail_pipeline v6.0の主要変更（2026-06-19）
- DB work queue導入: processed=0のDBレコードを直接再処理するパス追加
- 再分類パス: other判定レコードをルールベースで再判定→AI不要でproject昇格
- BTM/NBW regex修正: ENGINEER_PATTERNSの誤マッチ解消
- CostGuard v2統合: get_today_cost_usd()廃止、SQLite CostGuard一本化
- SQLite WAL + IMAPタイムアウト改善
- Notion登録リトライ + processed管理強化
- 分類ルール強化（単価表記・期間表記・募集キーワード等でproject優先判定）

### 4. CostGuard v2（2026-06-19 設定最適化）
| 項目 | 値 |
|---|---|
| 正本 | %LOCALAPPDATA%/ses_work_state/state.sqlite3 |
| 日次上限 | $8.00 |
| 月次上限 | $140.00 |
| PHASE_THRESHOLD_LIGHT | $1.00 |
| PHASE_THRESHOLD_MEDIUM | $2.00 |
| PHASE_THRESHOLD_HEAVY | $1.00 |
| DAILY_CALL_LIMIT_CLASSIFY | 500（バックログ消化用、定常時200に戻す） |
| DAILY_CALL_LIMIT_EXTRACT | 500（同上） |
| DAILY_CALL_LIMIT_MATCHING | 30 |
| fail-close方式 | CEO承認済み。エラー時は処理停止側に倒す |

### 5. matching（2026-06-19 精度改善）

#### webhook_server.py（Cloud Run）
- gross > 15除外 → スコア調整に降格（除外しない）
- スキル正規化: skill_utils.py共通モジュール（76行）
- 同義語辞書 + 部分一致 + NFKC正規化
- #skill_skip対応
- 除外理由stats追加

#### line_query.py
- 必須スキル空案件の全除外 → 撤廃
- gross > 15除外 → 撤廃
- #skill_skip対応追加
- skill_utils.py共通化

#### matching_v3（ローカル）
- ルールベースマッチング + LLM(gpt-4.1-nano)でメール文面生成
- skill_judge v3: CostGuard v2完全統合済み
- 平日8:00自動実行

### 6. LINE Webhook + LINE Bridge
| アカウント | URL | 状態 |
|---|---|---|
| 松野 | line-webhook Cloud Run | ✅ 稼働中 |
| 岡本 | 同上 /webhook_okamoto | ⏳ 岡本設定待ち |

- LINE Bridge: メッセージ振り分け + AI作業キュー
- push月200通上限。残0通時reply-onlyモード自動切替
- Cloud Scheduler 5分おきにworker自動起動

### 7. gate_checker v2.2（2026-06-19更新）
- GPT-4o + Claude Sonnet 4.6 並列レビュー
- DAILY_CALL_LIMIT=50
- 6フェーズ対応: research/requirements/design/pre_impl/implementation/test
- コスト通知Device 2、Notion AI作業キューDevice 3

### 8. nightly_jobz Phase 1（2026-06-19 新規）
| 項目 | 内容 |
|---|---|
| パス | ses_work/nightly_jobz/ |
| メイン | nightly_jobz.py (207行) |
| 処理 | task_processor.py (247行) |
| 状態 | DRY_RUN=1（Phase 1） |
| 起動 | 23:55（タスクスケジューラ未登録） |
| 予算 | $2/run (COST_GUARD_NIGHTLY_USD) |
| 対応種別 | investigation, spec_design |

### 9. freee請求書自動化
- freee_invoice_v2.py / 毎月1日09:00自動実行
- freee_invoice_monthly.py: 退役済み（CEO承認2026-06-19）
- 確定・削除は松野がfreee UIで手動操作

### 10. SESメール送受信（ses-mail）
- MCPサーバー: mail_mcp/mail_rest.py (754行、クラッシュ修正済み)
- jobz-command経由のみ動作

### 11. Notion DB
| DB名 | ID |
|---|---|
| エンジニアDB | 343450ff-37c0-819d-8769-fb0a8a4ceeb1 |
| 案件DB | 343450ff-37c0-81e4-934e-f25f90284a3c |
| AI作業キューDB | 37a450ff-37c0-819a-981b-c2e06ed282bb |
| SESナレッジWikiページ | 353450ff-37c0-8145-9e3e-d80c8c8ed594 |

## 2026-06-19 作業実績

### 完了タスク（17件 + 4件 = 21件）
| タスク | 内容 |
|---|---|
| A | BTM/NBW案件取りこぼし修正 |
| B | Notion登録失敗リトライ+processed管理 |
| C | pipeline CostGuard v2統合（fail-close） |
| D | 語彙外スキルREVIEW化 |
| E | soft-skill all-pass + Ruff/pyright導入 |
| F | freee monthly退役 + FT階段粗利 |
| G | SQLite WAL + IMAPタイムアウト |
| H | LINE push -1バグ修正 + UTC/JST日付境界 |
| I | 備考日数分岐 + human_reviewキーワード |
| J | gate_checker v2.2 + scheduler.py廃止 |
| K | PROCESS_LIMIT=100引き上げ |
| L | 分類精度改善（other→project漏れ修正） |
| M | gate_checker Gemini→Claude Sonnet差替え |
| N | Pipeline DB work queue統合 |
| O | nightly_jobz Phase 1 |
| P | matching webhook_server.py修正 |
| P2 | matching line_query.py統合修正 + skill_utils共通化 |

### 設定変更
| 設定 | 変更前 | 変更後 |
|---|---|---|
| PHASE_THRESHOLD_LIGHT | $0.025 | $1.00 |
| PHASE_THRESHOLD_MEDIUM | $0.10 | $2.00 |
| PHASE_THRESHOLD_HEAVY | $0.15 | $1.00 |
| DAILY_CALL_LIMIT_CLASSIFY | (default 50) | 500 |
| DAILY_CALL_LIMIT_EXTRACT | (default 50) | 500 |
| DAILY_CALL_LIMIT_MATCHING | (default 50) | 30 |

## 未完了タスク（引き継ぎ）

| タスク | 状態 | 対応方法 |
|---|---|---|
| Cloud Runデプロイ（matching修正反映） | 松野作業 | line_query.py + webhook_server.py + skill_utils.py |
| nightly_jobzタスクスケジューラ登録 | 松野作業 | 23:55毎日、DRY_RUN=1で開始 |
| 岡本LINE Webhook疎通確認 | 岡本設定待ち | 岡本からURL受領後に反映 |
| バックログ消化完了後のCostGuard定常値設定 | ジョブズ | CLASSIFY=200, EXTRACT=200に戻す |
| INFRA_SUMMARY PJファイル更新 | ジョブズ | 本文書をPJファイルとして置換 |
