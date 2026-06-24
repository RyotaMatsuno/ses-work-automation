# 全システム徹底調査レポート
日時: 2026-06-22

## サマリー
- 致命的 (P0): 10件
- 重要 (P1): 22件
- 改善推奨 (P2): 24件
- 情報 (P3): 14件

調査方法: 全モジュールのコードレビュー（mail_pipeline / analyze_final / matching_v3 / line_webhook / line_query / nightly_jobz / gate_checker / freee / local_server / cost_guard）、`raw_inbox.db` 整合性クエリ、分類精度テスト50件（実DB・seed=42）。

---

## P0: 致命的（即時対応必要）

### [P0-1] Batch API が CostGuard 予約を即解放（TOCTOU）
- 場所: `mail_pipeline/mail_pipeline.py:699-713`
- 影響: `allowed()` で予約後すぐ `finalize(transient)` し、実コストは後から `ledger_record()`。並列バッチで予算超過・dedup 契約破壊
- 再現手順: 複数 mail_pipeline プロセスで同時 classify batch 実行
- 推奨修正: batch 完了まで reservation を保持し、結果記録後に `finalize(success=True, tokens...)`

### [P0-2] CostGuard `can_spend()` DB エラー時 fail-open
- 場所: `cost_guard.py:680-683`
- 影響: ledger 読み取り失敗時 `budget_ok = True` → LLM が予算ガードなしで実行。fail-close 方針と矛盾
- 再現手順: ledger DB 破損/ロック中に `allowed()` 呼び出し
- 推奨修正: 例外時は `budget_ok = False`（blocked 扱い）

### [P0-3] IMAP TLS 証明書検証無効
- 場所: `mail_pipeline/mail_pipeline.py:558-560`
- 影響: MITM によるメール内容・IMAP パスワード窃取
- 再現手順: ポート 993 上の中間者攻撃
- 推奨修正: `CERT_NONE` / `check_hostname=False` を削除。dev のみ env で無効化

### [P0-4] 本番 LINE 照会が古い `line_query/` を import
- 場所: `line_webhook/webhook_server.py:1752-1753, 1788`
- 影響: Cloud Run 本番は `line_query/line_query.py` を使用。`line_webhook/line_query.py` の詳細コマンド・鮮度フィルタ・表示上限が未適用。テストと本番が乖離
- 再現手順: LINE で `詳細 ①` を送信 → 本番は `detail_query` 未実装のモジュールで処理
- 推奨修正: 単一 canonical モジュールに統合。webhook の import を `line_webhook.line_query` に変更

### [P0-5] 逆マッチングが必須スキル ANY 判定（1つ一致で通過）
- 場所: `line_webhook/webhook_server.py:535-537` / `line_query/line_query.py:360-362`
- 影響: 必須 `[Java, AWS, K8s]` の案件に Java のみのエンジニアがマッチ。`run_matching` は ALL 判定で非対称
- 再現手順: eng=`{skills:["Java"]}`, proj=`{required:["Java","AWS"]}` → reverse match 通過
- 推奨修正: 全経路で ALL-required に統一

### [P0-6] `skill_utils.skill_match` の部分文字列誤マッチ
- 場所: `line_webhook/skill_utils.py:57-60`
- 影響: `java` ⊂ `javascript`、`sql` ⊂ `mysql` 等で偽陽性。マッチング品質低下
- 再現手順: `skill_match("Java", {"javascript"})` → True
- 推奨修正: エイリアステーブルベースの完全一致。部分文字列マッチ廃止

### [P0-7] command_server + Cloudflare トンネル ≒ リモート RCE
- 場所: `local_server/command_server.py:33,219-328` / `line_webhook/remote_command_handler.py` / `config/.env` `JOBZ_COMMAND_URL`
- 影響: 固定トークン + `shell=True` + trycloudflare 公開で任意コマンド実行可能
- 推奨修正: トンネル停止、トークン env 化・ローテーション、コマンド allowlist、`shell=False`

### [P0-8] freee OAuth client secret のソースハードコード
- 場所: `freee_auth/token_manager.py:12-14`
- 影響: リポジトリ漏洩で freee API 完全侵害
- 推奨修正: env のみに移行、既存 secret ローテーション

### [P0-9] `run_monthly_invoice.bat` が廃止スクリプトを `--execute` で呼び毎月請求書未生成

- **場所**: `freee/run_monthly_invoice.bat:4`, `freee/register_monthly_task.bat`
- **影響**: タスクスケジューラが毎月 `freee_invoice_monthly.py --execute` を実行するが、廃止スクリプトは `sys.exit(0)` で即終了。freee への請求書が自動生成されず、exit=0 で成功扱いになるため異常を検知できない。→ **毎月の請求書が未送付になっている可能性がある（確認必須）**
- **再現手順**: タスクスケジューラで手動実行 → freee ダッシュボードで当月請求書の存在を確認
- **推奨修正**: `run_monthly_invoice.bat` の呼び出し先を `freee_invoice_v2.py --execute` に変更。`register_monthly_task.bat` も同様。

### [P0-10] `nightly_jobz/config.py` の `NIGHTLY_BUDGET_USD` がモジュールロード時（`load_env()` より前）に評価される

- **場所**: `nightly_jobz/config.py:33` — `NIGHTLY_BUDGET_USD = float(os.environ.get("COST_GUARD_NIGHTLY_USD", "2.0"))`
- **影響**: `main()` が `load_env()` (line 184) を呼ぶ前に `config` モジュールがロードされる時点でこの定数が確定する。`.env` の `COST_GUARD_NIGHTLY_USD` 値が `RunCostTracker` に反映されず、常にデフォルト値 `2.0` ドルで動作する。`get_dry_run()` は関数化で同問題を回避済みだが予算値は未対応。
- **推奨修正**: `def get_nightly_budget() -> float: return float(os.environ.get("COST_GUARD_NIGHTLY_USD", "2.0"))` に変更し、`RunCostTracker` 初期化時に呼ぶ。

---

## P1: 重要（今週対応）

### [P1-1] 処理例外で processed=1・retry なし
- 場所: `mail_pipeline/mail_pipeline.py:1924-2042`
- 影響: 一時障害メールが永久スキップ（`classify_result=error`）
- 推奨修正: Notion 失敗と同様 retry_count 連携、transient は processed=0 維持

### [P1-2] Batch classify が body 100文字のみ使用
- 場所: `mail_pipeline/mail_pipeline.py:1000`
- 影響: AI 分類で本文ほぼ未使用。engineer/project 判別精度低下
- 推奨修正: `body[:2000]` に拡張（extract パスと統一）

### [P1-3] legacy `classify_email` が 3 タイプ（engineer 含む）を返す
- 場所: `mail_pipeline/mail_pipeline.py:796-814, 1047-1048, 1940`
- 影響: v6「engineer→skip」方針と矛盾。Batch フォールバックで engineer 復活
- 推奨修正: 全経路を v2 `project|skip` に統一

### [P1-4] `skill_reader` が CostGuard v2 をバイパス
- 場所: `skill_reader/skill_reader.py:132-187` → `mail_pipeline.py:1604-1631`
- 影響: PDF/画像スキル抽出が `allowed/finalize` 未使用。dedup・call limit 外
- 推奨修正: `allowed(phase="extract")` / `finalize()` でラップ

### [P1-5] `mark_processed` UPSERT でスケルトン行生成可能
- 場所: `mail_pipeline/raw_inbox.py:283-292`
- 影響: `insert_raw_email` なしで processed=1 行が作成可能（過去に `message_id='abc'` で確認）
- 推奨修正: UPDATE-only または processed=1 時 classify_result 必須

### [P1-6] IMAP アカウント障害がサイレント（空配列返却）
- 場所: `mail_pipeline/mail_pipeline.py:564-566, 628-631`
- 影響: 1 アカウントの認証失敗でそのアカウントのメール全欠落。アラートなし
- 推奨修正: per-account 失敗を metrics/LINE に通知

### [P1-7] nightly_jobz 本番拒否パスで NameError
- 場所: `nightly_jobz/nightly_jobz.py:186-195`
- 影響: `NIGHTLY_DRY_RUN=0` かつ `ALLOW_PROD_WRITES!=YES` で `logger` 未定義
- 推奨修正: `_setup_logging()` を main 冒頭に移動

### [P1-8] Notion キューに claim / 冪等性なし
- 場所: `nightly_jobz/notion_queue.py:69-84`, `task_processor.py:237-247`
- 影響: `running` タスクが再取得され二重処理の可能性
- 推奨修正: 原子的 `queued→running` PATCH

### [P1-9] GPT 失敗時 Notion が `queued` のまま
- 場所: `nightly_jobz/nightly_jobz.py:165-175`
- 影響: CostGuard ブロック等で毎晩同タスクを再試行し続ける
- 推奨修正: 例外時に Notion を `blocked` に更新

### [P1-10] `run_monthly_invoice.bat` が退役スクリプトを呼び出し
- 場所: `freee/run_monthly_invoice.bat:4` → `freee_invoice_monthly.py`（即 exit 0）
- 影響: スケジュール実行しても請求書未作成。exit 0 で成功扱い
- 推奨修正: `freee_invoice_v2.py` に切替

### [P1-11] freee partner API に HTTP ステータス検証なし
- 場所: `freee/freee_invoice_v2.py:214-231`
- 影響: 401/500 時に KeyError またはサイレント失敗
- 推奨修正: status_code チェック + 認証失敗時バッチ abort

### [P1-12] `line_query` の粗利閾値が未適用
- 場所: `line_query/line_query.py:387, 404-407`（`GROSS_THRESHOLDS` 定義のみ）
- 影響: 岡本担当で gross 2万が通過（v3 では NG）
- 推奨修正: `if gross < threshold: continue`

### [P1-13] `handle_line_query` 不一致時 `None` 返却 → AI 分類にフォールスルー
- 場所: `line_query/line_query.py:525-530` / `webhook_server.py:1788-1798`
- 影響: 該当なし照会が登録フローに流入
- 推奨修正: 明示的「見つかりません」返却

### [P1-14] `matching_v3/skill_judge.py` がデッドコード
- 場所: `matching_v3/skill_judge.py` — `matcher.py` から未 import
- 影響: CostGuard 付き LLM スキル判定が未使用。未知スキルが MATCH を阻害しない
- 推奨修正: `judge()` に接続 or モジュール削除

### [P1-15] `analyze_final` 弱 project フォールバック
- 場所: `analyze_final.py:214-217`
- 影響: `[0-9]+万` 単独で project 判定。要員紹介メールの誤 project 化
- 推奨修正: `proj_score > eng_score` 必須化

### [P1-16] skill_extractor 誤マッピング
- 場所: `mail_pipeline/skill_extractor.py:141-157` — `c言語→Java`, `sql→MySQL`
- 影響: Notion 必要スキルが誤登録 → マッチング品質低下
- 推奨修正: 曖昧 alias 削除

### [P1-17] skill_extractor 辞書スキャンが全出現を required に
- 場所: `mail_pipeline/skill_extractor.py:194-197`
- 影響: 署名・フッターの incidental 言及が必須スキル化
- 推奨修正: ヘッダー抽出失敗時のみ辞書スキャン

### [P1-18] matching_v3 ERROR 案件が永久スキップ
- 場所: `matching_v3/processed_db.py:18-24`
- 推奨修正: ERROR 状態は再処理可能に

### [P1-19] structurer JSON 失敗 → 空案件でマッチング続行
- 場所: `matching_v3/structurer.py:171-209`
- 推奨修正: 低信頼度は REVIEW/SKIP 固定

### [P1-20] SES_MailPipeline 直近 exit 267009（タスク実行中）
- 場所: Windows Task Scheduler `\SES_MailPipeline`
- 影響: 二重起動・長時間処理の可能性
- 推奨修正: pipeline.lock 監視、legacy scheduler 停止確認

### [P1-21] GET エンドポイントに localhost ガードなし
- 場所: `local_server/command_server.py:128-185`
- 影響: トンネル経由で `/log`, `/health` が認証なしアクセス可能
- 推奨修正: 全エンドポイントに localhost チェック

### [P1-22] `FREEE_WRITE_APPROVED` と `.env` 値の不一致
- 場所: `freee_invoice_v2.py:341-343` / `config/.env`
- 影響: コードは `=1` 必須、`.env` は `false` → `--execute` 常時ブロック
- 推奨修正: 承認ワークフロー文書化

---

## P2: 改善推奨（次スプリント）

### [P2-1] nightly_jobz スケジューラは DRY_RUN=1 のみ（`.env` + bat 未上書き）

### [P2-2] lock 競合時 exit 0（成功扱い）— `nightly_jobz.py:63-74`, `mail_pipeline.py:271-281`

### [P2-3] briefing.json が早期終了時に未生成 — `nightly_jobz.py:131-135`

### [P2-4] Notion キュー pagination なし（limit=20 で打ち切り）

### [P2-5] IMAP FETCH_LIMIT がアカウントごと（最大 600 件/実行）

### [P2-6] `socket.setdefaulttimeout` グローバル変更 — `mail_pipeline.py:293-305`

### [P2-7] IMAP SINCE 7日固定 — 長期停止時に取込漏れ

### [P2-8] `line_query` 二重実装のドリフト（鮮度フィルタ・表示上限・詳細コマンド）

### [P2-9] `line_webhook/line_query.py` のハードコード日付カットオフ（2026-05-06/27）

### [P2-10] 勤務地フィルタ未実装（表示のみ）

### [P2-11] `#skill_skip` の適用タイミングが経路間で不一致

### [P2-12] `run_reverse_matching_full` が案件名のみで dedup

### [P2-13] `Notifier.PUSH_LIMIT_PER_DAY=6` がグローバル（ユーザー別でない）

### [P2-14] matching_v3 CostGuard 上限で mid-batch break（再開カーソルなし）

### [P2-15] legacy freee スクリプト残骸（`freee_invoice_monthly.py` dead code, `setup_all_tasks.bat` v1 参照）

### [P2-16] gate_checker `confidence < 0.6` ダウングレードが未実装（docstring のみ）

### [P2-17] gate_checker `call_gpt4o` デッドコード — `agreement_checker.run_dual_review` が実経路

### [P2-18] PROJECT_PATTERNS の `[0-9]+万` が広すぎ — `analyze_final.py:74`

### [P2-19] BODY_ENGINEER_STRONG と project subject の非対称判定

### [P2-20] price_extractor: 最新50件の teaser メール（本文リンクのみ）で回収率低下

### [P2-21] `resolve_final_price` が AI 価格 15-200 を無条件採用

### [P2-22] `remote_command_handler` cwd=`"ses_work"` 相対パス

### [P2-23] 複数 CostGuard 実装（root v2 vs `matching_v3/cost_guard.py`）

### [P2-24] Cloud Run gunicorn timeout 120s — 長時間 freee 操作に不足の可能性

---

## P3: 情報（記録のみ）

- bare except: `mail_pipeline.py:813,1086`、legacy freee/webhook 複数
- デッドコード: `gate_check.py:436-484`, `line_query.skill_match()`, `matcher.optional_skill_bonus_ok()`, `scheduler._scheduler_loop`
- ハードコード LINE user ID フォールバック（webhook_server, mail_pipeline）
- log 書き込み PermissionError 無視（OneDrive ロック）
- CostGuard finalize 例外 swallow（agreement_checker, task_processor）
- legacy classify_result ラベル（`person`, `candidate` 等）約39件
- retry_count 全件 0（リトライ機構が本番データで未発火）
- `ALLOW_PROD_WRITES` が `.env` に未定義
- 無効スケジューラタスク: `\SES_MatchingV3`, `\jobz_daily_report`, `\freee_auto_invoice` 等
- `matching_v3` 二重 weekday guard（`weekday_guard.py` + 内部）— 現状は整合
- `test_nightly_jobz_dry_run.py` が削除済み `config.DRY_RUN` を参照

---

## テスト実行結果

### 分類精度テスト A (50件, project のみ, seed=42)
- 実行: `mail_pipeline/_run_classify_test.py`
- 対象: `classify_result='project'` のメール 50件
- 一致: **42/50 (84.0%)**
- 不一致内訳: `project→engineer` 8件（100%）

解釈: DB ラベル `project` のうち 8件は件名/本文に人材キーワード（`【直人材】`, `要員情報` 等）があり、ルールは `engineer` と判定。ルールの誤りというより DB ラベル汚染（Recall-first AI パイプライン由来）の可能性が高い。

### 分類精度テスト B（多カテゴリ50件 — 2026-06-22 実測）

各カテゴリから按分サンプリング（project:20, skip:15, other:12, person:3）し、`classify_by_rule(subject, sender, body)` を実行。ラベルマッピング: `engineer→person`、`unknown→other`。

| カテゴリ | 正解/サンプル | 精度 |
|---|---|---|
| project | 17/20 | 85% |
| skip | 1/15 | 7% |
| other | 0/12 | 0% |
| person | 3/3 | 100% |
| **合計** | **21/50** | **42%** |

**解釈**: `skip` の低精度 (7%) は、DB の `skip` レコードの大半が BP 会社のエンジニア紹介メール（rule→`engineer`）であるため。pipeline では `engineer → skip` に正変換されるので実運用上の誤分類率は見かけより低い。**真の問題は `other` 0%** — ニュースレター・告知・商材紹介メールが rule で `project` または `person` に誤判定される。

主な誤分類パターン:
| 期待(DB) | rule出力 | 件名例（抜粋） |
|---|---|---|
| skip | person | ★★おすすめ人材！Python【フリテク押田】 |
| skip | project | プロダクトマネージャー案件/〜100万/ファンクラブSNS |
| skip | other | 【明日12時】商談準備〜実施を、AIで標準化する方法 |
| other | person | 【SasaTech 人材】TypeScript/Go 90万 |
| other | project | 【BTM案件】M365 大手町 |

### raw_inbox.db 整合性（2026-06-22 再確認）
| 指標 | 値 |
|------|-----|
| 総件数 | 5,495 |
| processed=1 & classify=NULL | **0** |
| message_id 重複 | **0** |
| retry_count > 5 | **0** |
| classify 内訳 | skip:1,579 / migrated:1,560 / other:1,078 / project:938 / NULL:301 / legacy:~39 |

### Task Q 回収率（同日実装・rule-only シミュレーション）
| サンプル | No skills | No price | 目標 |
|----------|-----------|----------|------|
| 50件（直近 DESC） | 36.0% | 56.0% | ≤35% / ≤25% |
| 50件（ランダム seed=42） | — | 38.0% | — |
| 全 project 897件 | 25.8% ✓ | 33.2% | ≤35% / ≤25% |

注: 直近50件の 27/50 が本文200文字未満の teaser メール（NALU リンクのみ）で単価情報なし。rule-only では回収不可。AI+rule 統合（`resolve_final_price`）は `register_project` に組込済み。

### Task Q ユニットテスト
- `mail_pipeline/tests/test_task_q_extraction.py`: **15/15 passed**

---

## 推奨アクション一覧（優先順）

1. **即日**: freee ダッシュボードで当月請求書の存在を確認（P0-9 実害確認）
2. **即日**: `run_monthly_invoice.bat` → `freee_invoice_v2.py --execute` に切替（P0-9）
3. **即日**: Cloudflare トンネル停止 + JOBZ トークン/env 秘密情報ローテーション（P0-7）
4. **即日**: freee OAuth secret のソース除去（P0-8）
5. **即日**: webhook の `line_query` import 統一（P0-4）
6. **今週**: `nightly_jobz/config.py` NIGHTLY_BUDGET_USD を関数化（P0-10）
4. **今週**: マッチング skill 判定 ALL-required + 部分文字列修正（P0-5, P0-6）
5. **今週**: mail_pipeline batch CostGuard 契約修正（P0-1, P0-2）
6. **今週**: IMAP TLS 検証復活（P0-3）
7. **今週**: 処理例外時 retry 設計（P1-1）
8. **今週**: nightly_jobz logger NameError + Notion キュー claim（P1-7, P1-8）
9. **今週**: `run_monthly_invoice.bat` → v2 切替（P1-10）
10. **今週**: analyze_final 弱フォールバック修正（P1-15）
11. **次スプリント**: skill_extractor alias / 辞書スキャン修正（P1-16, P1-17）
12. **次スプリント**: line_query 二重実装統合（P2-8）
13. **次スプリント**: スケジューラ整理（無効タスク・SES_MailPipeline 267009 調査）

---

## 調査対象外・制約
- `config/.env` の値は記載せず（変数名と存在確認のみ）
- 本レポートは修正を行わず記録のみ（Investigation R 仕様準拠）
- Cloud Run 本番 env はローカルから未検証
