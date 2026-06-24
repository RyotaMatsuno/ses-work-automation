# R13: LINE bridge 調査
調査日: 2026-06-18

## 結論（1行）
振り分け・キュー登録・5分cronの骨格は動くが、`handle_router_message` 未配線・引き継ぎ(jobz)タスクのワーカー対象外・push上限150のreply-only未実装・quota取得失敗時のpush試行・Scheduler二重実行時の競合が主要リスク。

## 振り分けロジック
| カテゴリ | 判定条件 | 漏れリスク |
|---|---|---|
| **即時（immediate）** | ①イニシャル+地名（`_INITIAL_PLACE_RE`）②`/` 始まり ③`IMMEDIATE_WORDS` 部分一致（「今日の案件」「進捗」「案件」「人材」等）④80文字以上 | **中**: 80字以上の非マッチング指示は無条件で即時系へ。`IMMEDIATE_WORDS` の「進捗」部分一致により「作業進捗」等も即時pass（後段 webhook の substring ハンドラに依存） |
| **営業重作業（sales）** | `SALES_HEAVY_WORDS` 部分一致（重作業/深掘り/提案文/評価表/意向確認文/面談調整）→ assignee=girard | **低**: 経理・開発キーワードより後段のため、複合文は他カテゴリ優先 |
| **経理（accounting）** | `ACCOUNTING_WORDS` 部分一致（請求/入金/契約マスター/freee等）→ shibusawa | **低**: `classify_route` 内で開発・営業より**先**に判定 |
| **開発（development）** | `DEVELOPMENT_WORDS` 部分一致 → codex/cursor。enqueue 時 `状態=blocked`（自動処理対象外） | **低**: 意図的にワーカー非実行 |
| **要確認（ambiguous）** | 上記いずれにも該当せず **80字未満** → 1問確認（1/2/3/4）→ 600秒TTL | **中**: 確認replyが `ROUTE_CHOICES` 外なら「判定できないためキュー未登録」で終了（最大1往復）。`immediate` 選択時は元文を即時系へ委譲 |
| **引き継ぎ（research/jobz）** | `_HANDOFF_MARKERS`（■/【/】/最優先/未完了）の**いずれか**を含む → `_HANDOFF_SECTION_RE` で ■セクション抽出 | **高**: マーカーだけ（【】のみ等）で `_extract_handoff_tasks` が空なら **None 返却→通常振り分けへ**。■見出し形式でない箇条書きは登録されない |
| **タスク回答** | `^#(T\d+)\s+(.+)$` 完全一致 | **低** |
| **非松野ユーザー** | `user_id != MATSUNO_USER_ID` → `action=pass` | 設計通り（既存 webhook 処理へ） |

**優先順位（`classify_route`）**: イニシャル/`/` → 経理 → 開発 → 営業重 → 即時KW → 80字以上 → ambiguous

**「進捗」コマンド（完全一致）** — `handle_router_message`（`line_bridge.py:892-908`）:
| 入力 | 動作 |
|---|---|
| `作業進捗` | `build_queue_progress(limit=10)` |
| `進捗` | 3種類の案内メッセージ |
| `案件進捗` / `人員進捗` | 「準備中」 |
| `確認済み` | human_review_items クリア |

⚠️ **配線ギャップ**: 本番 `webhook_server.py` は `route_line_message` を直接呼び **`handle_router_message` は未使用**。進捗系は L1899 の `"進捗" in text and len<=10`（部分一致）で処理され、案件DB進捗 + AIキュー進捗を返す。完全一致仕様と実挙動が不一致（例: 「進捗どう」も substring で反応、`handle_router_message` テスト期待とは逆）。

## 引き継ぎパーサー
- **■セクション正規表現**（B方式）:
  - 見出し: `■\s*(?:最優先|未完了[・･]?続きが必要なもの|次チャットで最初にやること)`（`_HANDOFF_SECTION_RE`）
  - 箇条書き: `^\s*(?:[-－ー•·]|・|\d+[.)．、])\s*(.+?)\s*$`（`_HANDOFF_BULLET_RE`）
- **検出マーカー**: `("■", "【", "】", "最優先", "未完了")` — 【】1文字でも handoff 経路に入る
- **フォールバック**: タスク0件 → `None`（サイレント）。通常 `classify_route` へ。登録成功時 reply「N件をキューに登録しました」
- **Notion登録**: `enqueue_task()` → `POST https://api.notion.com/v1/pages`（DB=`NOTION_AI_QUEUE_DB_ID`、デフォルト `37a450ff-...`）。route=`research`, assignee=`jobz`, 状態=`queued`
- **重大ギャップ**: `_query_queued()` は **girard / shibusawa のみ**取得（L940-968）。引き継ぎ jobz タスクは **キューに積まれるが `pickup_and_run` では処理されない**

## ThreadPoolExecutor安全性
- **max_workers=5**: `line_bridge/SPEC.md` の並列設計（Cloud Run `--max-instances=5`, `--concurrency=1`）に対応。1 cron あたり最大5タスク同時 LLM 実行
- **負荷**: デフォルト `LINE_BRIDGE_PICKUP_LIMIT=50` 件を query 後、最大5並列。各タスク `guarded_anthropic_call` timeout=90s → 最悪 ~450s 相当だが gunicorn `--timeout 120` で Cloud Run 側が先に切れる可能性
- **スレッド内例外**: `_process_single_task` が全例外 catch → 当該タスクのみ `blocked`、他スレッド継続。**良好**
- **競合防止（同一タスク）**: `queued→running` PATCH 後 GET で status 確認。Notion に原子 CAS がないため **Scheduler 二重起動時に同一タスク二重処理の余地あり**
- **タイムアウト**: `future.result()` に **timeout なし**。1スレッド hang で worker エンドポイント全体がブロックしうる
- **CostGuard**: スレッド間は `threading.Lock()` で日次/月次 USD 管理。上限超過は当該タスクのみ `CostLimitError→blocked`

## push上限管理
| 項目 | 実装 | 評価 |
|---|---|---|
| **`push_or_log()`** | `_line_push_remaining()` で quota/consumption API 取得 → `remaining != 0` なら push → 失敗時 Notion に `push_fail_*` または既存 task の結果リンク追記 | **部分対応** |
| **残通数取得** | LINE API `GET /v2/bot/message/quota` + `/quota/consumption`。エラー時 **-1** | API ベース（ローカルカウンターなし） |
| **月次リセット** | LINE 側の公式 quota リセットに依存。コード側リセット処理なし | 設計通り |
| **150通 reply-only** | `INFRA_SUMMARY_20260610.md` に記載あるが **`push_or_log` / `webhook_server.push_message` いずれにも未実装**。残0のときのみ push スキップ | **未実装（仕様とコード乖離）** |
| **`remaining == -1` 時** | `remaining != 0` が真のため **push を試行**（quota 不明でも送信） | **バグ** |
| **`consume_completion_push_budget()`** | 当月完了タスク数 vs `LINE_BRIDGE_PUSH_MONTHLY_LIMIT`(default 20) を Notion カウント。`webhook_server` に import されるが **呼び出し箇所なし**（2026-06-15 完了push廃止後の死コード） |
| **webhook 直 push** | `push_message()` は quota チェックなしで Messaging API push（マッチング複数チャンク等） | reply 無制限だが **push 枠を直接消費** |
| **利用箇所** | mail_pipeline, sheets_reader, freee_invoice_v2, metrics_daily_summary 等が `push_or_log` 使用 | gate_checker は TASKS.md 上は未配線 |

## Cloud Scheduler連携
- **エンドポイント**: `POST /line-bridge/worker`（`webhook_server.py:2445`）。併せて `POST /line-bridge/expire`（失効専用）
- **スケジュール**: `*/5 * * * *`（ジョブ名 `line-bridge-worker-cron`, asia-northeast1）— `line_bridge/SPEC.md` 記載
- **認証**: ヘッダー `X-Line-Bridge-Token` == env `LINE_BRIDGE_CRON_TOKEN`（空なら **403**）。`cron_authorized()` / `worker_authorized()` 同一
- **処理内容**: `pickup_and_run()` →（push は 2026-06-15 廃止、`pushed=0` 固定）→ `expire_finished()` 同梱
- **二重実行防止**: **なし**（分散ロック・idempotency key なし）。Cloud Run `--concurrency=1` はインスタンス内のみ。5分 overlap や手動 trigger 併用時は queued タスクの二重 pickup リスク
- **監視**: `line_bridge/check_worker_health.py` が worker POST + Notion キュー監視（running 30分 stale 検知）。異常時は **push 直叩き**（`push_or_log` 非経由）

## 推奨アクション
- [ ] **P0**: `webhook_server.process_message` を `handle_router_message` 経由に統一し、進捗コマンドの完全一致/substring 二重定義を解消
- [ ] **P0**: `push_or_log` を `remaining > 0` のみ push に修正（`-1` は Notion ログのみ）。残 **≤150** で reply-only フラグを実装し `push_message` 直叩き箇所にも適用
- [ ] **P0**: 引き継ぎ(jobz/research)タスクのワーカー方針を決定 — `_query_queued` 拡張 or jobz 専用処理 or 登録時に blocked+手動明示
- [ ] **P1**: Scheduler 二重実行対策 — Notion `queued→running` を条件付き更新相当（取得直後再query + page_id 単位ロック）または Cloud Scheduler `attemptDeadline` / 実行中スキップ
- [ ] **P1**: `pickup_and_run` の `future.result(timeout=...)` と Cloud Run timeout の整合（120s 内に収める pickup limit 見直し）
- [ ] **P1**: 引き継ぎパーサー — マーカー検出と ■セクション不一致時に「形式エラー」を reply（サイレント fallthrough 廃止）
- [ ] **P2**: 未使用 `consume_completion_push_budget` import を削除 or 再配線の方針決定
- [ ] **P2**: `check_worker_health.send_line_alert` を `push_or_log` 経由に変更（quota 管理の一元化）
- [ ] **P2**: gate_checker の残80/150通閾値を `push_or_log` オプション引数として実装（現状 TASKS.md のみ）
