# R09: mail_pipeline IMAP・並行安全性調査
調査日: 2026-06-18

## 結論（1行）
IMAPは7日間SINCE＋アカウント別最新200件取得・Message-IDで重複排除・1回50件処理だが、接続リトライ・IMAPタイムアウト・アプリ内ロックがなく、スケジューラ二重系と「例外でもfinallyでprocessed化」により取りこぼし・見逃しリスクが残る。

## IMAP接続設定

| 項目 | 実装値 | 根拠 |
|---|---|---|
| サーバー / ポート | `mail65.onamae.ne.jp:993`（デフォルト） | `mail_pipeline.py:100-101` `OUTLOOK_IMAP_SERVER` / `OUTLOOK_IMAP_PORT` |
| プロトコル | `imaplib.IMAP4_SSL` | `mail_pipeline.py:429` |
| SSL/TLS | `ssl.create_default_context()` + **`check_hostname=False` / `verify_mode=CERT_NONE`** | `mail_pipeline.py:425-427`（証明書検証無効） |
| 接続タイムアウト | **未設定**（`imaplib` デフォルト＝事実上無制限） | `fetch_emails_from_account()` に `socket` / `timeout` 指定なし |
| リトライ | **なし**（1回失敗で `return []`） | `mail_pipeline.py:432-434` |
| 認証情報 | `config/.env` → `dotenv_values` で `os.environ` へ投入 | `mail_pipeline.py:73-98, 102-120` |
| アカウント | 共通（`OUTLOOK_EMAIL`/`OUTLOOK_PASSWORD`）＋任意で松野・岡本 | `EMAIL_ACCOUNTS` 配列 |
| 対象フォルダ | `INBOX` のみ | `mail_pipeline.py:431` |

**認証の取得経路**

```
config/.env
  OUTLOOK_IMAP_SERVER, OUTLOOK_IMAP_PORT
  OUTLOOK_EMAIL, OUTLOOK_PASSWORD
  MATSUNO_EMAIL, MATSUNO_PASSWORD（任意）
  OKAMOTO_EMAIL, OKAMOTO_PASSWORD（任意）
```

ハードコードはサーバー名・ポートのデフォルト値のみ。パスワードはコード内にない。

**接続失敗時の挙動**

- ログ `IMAP接続エラー ({user}): {e}` を出し、そのアカウント分は空リスト
- 他アカウントは継続
- **`metrics.imap_errors` はインクリメントされない**（フィールド定義のみ、`mail_pipeline.py` 内で `inc("imap_errors")` 呼び出しなし）

## フェッチ・処理フロー

### FETCH_LIMIT=200 / PROCESS_LIMIT=50

| 定数 | 値 | 適用箇所 |
|---|---|---|
| `FETCH_LIMIT` | 200 | `main()` → `fetch_recent_emails(limit=fetch_limit)` |
| `PROCESS_LIMIT` | 50 | `new_emails[:process_limit]` |

`RECOVERY_MODE=true` 時のみ `recovery_state.json` のフェーズ別 limit で上書き（現状 `day0_emergency`: fetch=50, process=10）。通常は定数 200/50。

### フェッチ条件（UNSEEN ではない）

```python
# mail_pipeline.py:436-446
since_date = (date.today() - timedelta(days=7)).strftime("%d-%b-%Y")
status, messages = mail.search(None, f"SINCE {since_date}")
target_ids = list(reversed(all_ids[-limit:]))  # 7日以内のうち最新 limit 件
```

- **未読（UNSEEN）ではない** — 直近7日の全メールから最新200件（アカウントごと）
- 3アカウント合計最大約600件（`msg_id` で重複除去後）
- 古い SPEC.md の「UNSEENのみ」は現行 v6.0 と不一致

### 200件フェッチ → 50件処理 → 残りの扱い

```
fetch_recent_emails(200/アカウント)
  → raw_inbox.db に全件 INSERT（新規のみ）
  → load_processed_ids() で processed=1 の Message-ID を除外
  → new_emails[:process_limit] のみ LLM分類・Notion等
  → ループ finally で save_processed_id()（processed=1）
```

- **残りの new_emails（51件目以降）は次回実行で再対象**（processed フラグ未設定のため）
- **ただし次回も同じ200件ウィンドウ内に収まる必要あり** — 7日以内に200件超の新着が続くと、古い未処理メールはフェッチ対象外になり取りこぼしうる

### 再フェッチ防止

| 層 | 仕組み |
|---|---|
| 処理済み判定 | SQLite `raw_emails.processed=1`（旧 `processed_ids.json` は起動時マイグレーション） |
| キー | RFC `Message-ID` ヘッダ（無い場合は `no-id-{imap_seq}-{user}`） |
| マルチアカウント重複 | `fetch_recent_emails` 内で `msg_id` の `seen_ids` セット |
| raw保存 | フェッチ直後に `insert_raw_email`（分類前）— 取りこぼしゼロ基盤 |

### processed 判定タイミング

| タイミング | 内容 |
|---|---|
| フェッチ時 | **processed にはしない**（raw_inbox に `processed=0` で保存のみ） |
| 分類後 | `update_classify_result()` で `classify_result` 更新 |
| 各メール処理後 | **`finally` で必ず `save_processed_id()`** — 成功・失敗・例外問わず |
| Notion失敗時 | `register_project` 失敗でも `save_processed_id` 後 `continue`（再処理されない） |
| 途中クラッシュ | Python プロセスごと落ちた場合、そのメールは processed 未設定 → **次回再処理** |
| 例外スキップ | `except` でログ後 `finally` が走るため **processed 化され再処理されない**（欠落リスク） |

**トレードオフ（SPEC_costfix 意図）**: 無限再処理ループ防止のため「例外でも processed」だが、分類・Notion未完了メールは永久スキップになりうる。raw_inbox には本文が残る。

## 並行実行安全性

### mail_pipeline.py 本体

- **PIDファイル / flock / SQLiteロックなし**
- 同一 `raw_inbox.db` への同時書き込みは SQLite のデフォルト挙動に依存（明示排他なし）

### スケジューラ側

| 機構 | 設定 | 効果 |
|---|---|---|
| Windows タスク `SES_MailPipeline` | `MultipleInstancesPolicy: IgnoreNew` | 前回実行中は新インスタンス起動を無視 |
| 同上 | `ExecutionTimeLimit: PT1H` | 1時間で強制終了 |
| `local_server/scheduler.py` | `job_state/mail_pipeline_hourly.lock`（PIDファイル, O_EXCL） | 時間軸スケジューラ内の二重起動防止 |
| 同上 | `threading.Lock` + `is_running()` | 同一プロセス内の重複実行防止 |

**二重スケジューラ共存**

1. **Windows Task Scheduler** — 初回登録は30分間隔（`schtasks /mo 30`）。バックアップ XML（2026-06-18）は **1時間間隔（PT1H）** で `wd_mail_pipeline.bat` 実行
2. **`local_server/scheduler.py`** — command_server 起動時に **毎時** バックグラウンド実行（catch-up 最大3スロット）

両方が有効だと、別経路から同時起動しうる。タスク側 `IgnoreNew` と scheduler 側 PID ロックは**相互に認識しない**。

### 30分（または1時間）間隔 × 処理30分超

`job_state/mail_pipeline_hourly.json` の実績例:

- 15:00 開始 → 15:49 終了（約49分）
- 17:00 開始 → 17:35 終了（約35分）

`IgnoreNew` のため、処理が次スロットをまたぐと **そのスロットの実行はスキップ**（ログに残らない）。バックログは次回の `new_emails[:50]` で徐々に消化する設計だが、スキップされたスロット分の「追加取得」は発生しない。

## 17時間スキップ再発リスク

### 既知事故（調査指示の「17時間」≒ 社内記録の16時間）

- **期間**: 2026-06-17 20:00 〜 2026-06-18 11:00（約15〜16時間、`wall_hitting_bugs_round5`）
- **最有力原因**: PCスリープ中のトリガー喪失 + `StartWhenAvailable` 未設定（または false）+ `UseUnifiedSchedulingEngine=true`
- **副次要因**: 2026-06-18 11:54 の `Set-ScheduledTask`（RestartCount=3 追加）直後、12:00 トリガーがスキップされた事例

### タスクスケジューラ設定（バックアップ XML 時点）

| 設定 | 値 | 再発リスク |
|---|---|---|
| 実行中の場合 | `IgnoreNew` | 長時間実行中は次回丸ごとスキップ |
| `RestartCount` / `RestartInterval` | バックアップ XML に**記載なし**；6/18 に `RestartCount=3`, `PT1M` 追加作業あり | 起動失敗時の再試行は設定済みの可能性（要実機確認） |
| `StartWhenAvailable` | バックアップ XML に**記載なし**（デフォルト false 想定） | スリープ復帰後の未実行補填なし → **高リスク** |
| `DisallowStartIfOnBatteries` | true | バッテリー駆動時は起動しない |
| 実行ラッパー | `weekday_guard.py` → 土日祝は **exit 0 で即終了** | 休日は意図的スキップ |

### 長時間未実行の検知・アラート

| 機構 | 有無 |
|---|---|
| `metrics.jsonl` + 実行後 LINE push | あり（毎回）— 未実行そのものは検知しない |
| `metrics_daily_summary.py` | 23:00 日次サマリー — **実行回数ゼロは「データなし」表示のみ** |
| `job_state/mail_pipeline_hourly.json` | `last_success_at`, `last_skipped_slot` — scheduler 経由のみ |
| ギャップ検知（例: 2時間以上未実行でアラート） | **なし** |
| catch-up | `scheduler.py` で最大3時間分補填 — **Task Scheduler 経路には未適用** |

## 推奨アクション

- [ ] **IMAP接続に `socket.setdefaulttimeout(60)` または `IMAP4_SSL(..., timeout=60)` を追加**し、ハングを防止する
- [ ] **IMAP接続失敗時に指数バックオフで2〜3回リトライ**し、失敗時は `metrics.inc("imap_errors")` を記録する
- [ ] **`fetch_emails_from_account` 失敗時に exit_code≠0 または LINE 異常通知**（現状は空リストで正常終了しうる）
- [ ] **7日×200件ウィンドウ外の未処理検知** — `raw_inbox` で `processed=0` かつ `received_at` が古い件数を metrics / 日次サマリーに出す
- [ ] **例外時の processed 方針を見直し** — `finally` 一括 processed をやめ、Notion成功時のみ processed、または `processed` と `classify_result='error'` を分離して再処理可能にする
- [ ] **スケジューラを一本化**（Task Scheduler **または** `local_server/scheduler.py`）し、二重起動経路をなくす
- [ ] **Task Scheduler に `StartWhenAvailable=true` を管理者権限で設定**し、スリープ復帰後の missed trigger を回収する
- [ ] **タスク更新は次回トリガーの15分以上前に限定**（11:54更新→12:00スキップの再発防止）
- [ ] **長時間未実行アラート** — `last_success_at` から90分以上経過で LINE 警告（`job_state` または `metrics.jsonl` 最終行を監視）
- [ ] **`RECOVERY_MODE` 無効時も `recovery_state.json` と実 limit の乖離をドキュメント化**（調査時点: 定数200/50が有効、recovery_state の 50/10 は `RECOVERY_MODE=true` 時のみ）
