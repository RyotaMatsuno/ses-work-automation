# R10: mail_pipeline テスト・エラー処理調査
調査日: 2026-06-18

## 結論（1行）
pytest 35件は全パス（4 skip）だが `mail_pipeline.py` 本体・Batch API・IMAP/Notion 経路はほぼ無テストで、CostGuard v2 / `DAILY_CALL_LIMIT` 未統合・`main()` が exit code を返さないなど本番障害リスクが残存。

## テスト実行結果
| テストファイル | Pass | Fail | Skip |
|---|---|---|---|
| test_analyze_final.py | 4 | 0 | 0 |
| test_metrics_recorder.py | 6 | 0 | 0 |
| test_notion_engineer_payload.py | 4 | 0 | 4 |
| test_raw_inbox.py | 6 | 0 | 0 |
| test_recovery_mode.py | 11 | 0 | 0 |
| **合計** | **31** | **0** | **4** |

**スキップ詳細（4件）**: `test_notion_engineer_payload.py` の `test_case_a`〜`test_case_d` — `RUN_NOTION_LIVE_TESTS=1` 未設定のため本番 Notion API テストをスキップ。

**失敗テスト**: なし。

**テストケース数**: 35件（Pass 31 + Skip 4）。

## カバレッジ不足箇所
| モジュール | テストなし関数 | リスク |
|---|---|---|
| `mail_pipeline.py` | `call_claude`, `classify_email`, `classify_email_v2`（Batch API 含む）, `extract_affiliation`, `ai_matching`, `double_check` | LLM 分類・マッチング・ダブルチェックの本番経路。CostGuard 漏れ・JSON パース失敗時のサイレント劣化 |
| `mail_pipeline.py` | `fetch_emails_from_account`, `fetch_recent_emails`, `decode_str`, `get_body_and_attachments` | IMAP 接続・メール解析の障害がテストで検知不可 |
| `mail_pipeline.py` | `register_project`, `register_engineer`, `notion_query`, `update_page_properties`, `send_proposal_email` | Notion/SMTP 書き込み失敗・payload 不整合が本番初出 |
| `mail_pipeline.py` | `main`, `_main_body`, `_save_all_emails_to_raw_inbox`, `_push_metrics_line`, `_handle_recovery` | オーケストレーション全体・DRY_RUN 分岐・メトリクス/LINE push |
| `mail_pipeline.py` | `get_today_cost_usd`, `filter_engineers_by_skills`, `process_skill_sheet`, `save_draft` | コストガード判定・スキルフィルタ・下書き生成の回帰検知なし |
| `raw_inbox.py` | `update_classify_result`, `count_rows`, `count_processed`, `body_hash`（直接） | 分類結果の DB 更新・統計集計の不整合 |
| `analyze_final.py` | `__main__` ブロック（コスト試算スクリプト） | 本番パイプライン非経路のため低リスク。`classify_by_rule` のみ 4 テストあり |

**テストあり（参考）**: `raw_inbox` 6関数、`recovery_mode` 全主要関数、`MetricsRecorder`、`classify_by_rule`（4パターン）、`validate_engineer_payload`（インライン実装コピーで検証 — 本物 `mail_pipeline.validate_engineer_payload` とは別実装）。

## CostGuard適用状況
| LLM呼び出し箇所 | CostGuard | モデル | max_tokens |
|---|---|---|---|
| `call_claude()` L530（`classify_email`, `extract_affiliation`, `ai_matching`, `double_check` 経由） | **部分** — `get_today_cost_usd() >= DAILY_COST_LIMIT_USD($2.0)` のみ。`cost_guard.py` / `ledger.reserve()` / `DAILY_CALL_LIMIT` **未使用** | `claude-haiku-4-5-20251001` | 50〜2000（呼び出し元依存） |
| `classify_email_v2()` → `send_batch()` L653（Batch API 直接 `requests.post`） | **なし** — 日次コストチェック・`log_cost()` 記録ともにバイパス | `claude-haiku-4-5-20251001` | 50（分類）/ 400（抽出） |
| `classify_email_v2()` フォールバック → `classify_email()` | 上記 `call_claude` の部分ガードのみ | 同上 | 1500（デフォルト） |

**補足**:
- OpenAI / `gpt-` / `responses.create` の呼び出しは `mail_pipeline/` 内に**なし**（Anthropic Haiku のみ）。
- 成功時は `usage_tracker.cost_logger.log_cost()` で `cost_log.jsonl` に記録されるが、Batch API 経路は記録されない。
- `cost_guard_v2/TASKS.md` 7.3「`mail_pipeline.py` を `cost_guard.allowed()` 経由に置換」は **未完了**。
- `DAILY_CALL_LIMIT=30`（`common/ledger.py` の `DAILY_CALL_LIMIT_DEFAULT`）は **mail_pipeline 未適用**。現行はドル上限 `$2.0/日`（`DAILY_COST_LIMIT_USD`）のみ。
- `get_today_cost_usd()` が例外時 `0.0` を返すため、ログ読み取り失敗時はガードが無効化される。

## エラーハンドリング評価

### try/except カバー範囲
- **広すぎる `except:`（バア except）**: `classify_email` L587、`ai_matching` L818 — JSON パース失敗を握りつぶし `other`/空候補を返す。意図的だがデバッグ困難。
- **メール単位の `except Exception`**: `_main_body` L1678 — 1件の失敗でスキップし `finally` で processed 化。パイプライン全体は継続（非致命的）。
- **`main()` トップレベル**: L1499 — 致命例外をキャッチし `metrics.finalize(exit_code=1)` するが、**`sys.exit()` を呼ばない**ためシェル/Task Scheduler は常に exit 0。

### ログ粒度
- エラーはほぼ `log(f"...: {e}")` の文字列のみ。**`traceback` / `exc_info` 未使用** — スタックトレースは `pipeline.log` に出ない。
- Batch API 失敗時は `RuntimeError`/`TimeoutError` を raise 後、外側でフォールバック（L779）— 原因は1行ログのみ。

### 致命的 vs 非致命的
| 種別 | 挙動 | 例 |
|---|---|---|
| 非致命的 | ログして継続 | IMAP 1件取得失敗、メール1件処理例外、Notion 1件登録失敗（`continue`） |
| 準致命的 | metrics `exit_code=1` 記録だがプロセスは 0 終了 | `main()` 未捕捉例外 |
| コスト上限 | API スキップ（空文字返却） | `call_claude` の `$2/日` 到達 |

### exit code
- `main()` / `if __name__ == "__main__"`: **`sys.exit` なし** — Task Scheduler・recovery_mode の `exit_code` 判定（metrics 内記録）と実プロセス終了コードが乖離。
- `exit(2)` の使用: **なし**。
- `test_raw_inbox.py`（tests 外のスタンドアロン）: `sys.exit(0|1)` あり。

### 設定値
| 設定 | 定義場所 | 変更容易性 |
|---|---|---|
| `FETCH_LIMIT=200`, `PROCESS_LIMIT=50` | `mail_pipeline.py` L82-83 定数 | コード変更が必要。`RECOVERY_MODE=true` 時は `recovery_mode.PHASE_SETTINGS` で上書き（day0: 50/10 → day3: 200/50） |
| `DAILY_COST_LIMIT_USD=2.0` | `mail_pipeline.py` L92 | コード変更が必要 |
| `MATCH_TOP_N=10` | L84 | コード変更が必要 |
| IMAP `since_days=7` | `fetch_emails_from_account` デフォルト引数 L419 | 関数引数で変更可（呼び出し元は固定 7） |
| Claude API timeout | L550,660,671: 60s / batch poll: 120min / results: 120s | ハードコード |
| Notion API timeout | L835,867,936: 30s | ハードコード |
| IMAP timeout | **未設定**（`imaplib` デフォルト） | — |

### DRY_RUN / DRY_RUN_PROCESS_EMAILS
| 条件 | 挙動 |
|---|---|
| `DRY_RUN=1` かつ `DRY_RUN_PROCESS_EMAILS≠1` | `_main_body` 冒頭で即 return — IMAP/Notion/送信すべてスキップ（起動確認のみ） |
| `DRY_RUN=1` | `update_page_properties`, `send_proposal_email`, `register_project`, `register_engineer` を個別スキップ |
| `DRY_RUN_PROCESS_EMAILS=1` | 上記早期 return をバイパスし、メール処理フローに入る（個別 DRY_RUN ガードは残る） |

## 推奨アクション
- [ ] **P0**: `classify_email_v2` の Batch API に `call_claude` 同等のコストガード + `log_cost()` 記録を追加（現状最大のコスト暴走経路）
- [ ] **P0**: `mail_pipeline.py` を `cost_guard.allowed()` / `finalize()` + `ledger.reserve(DAILY_CALL_LIMIT)` に統合（`cost_guard_v2/TASKS.md` 7.3 完了）
- [ ] **P0**: `main()` 終了時に `sys.exit(final_metrics.get("exit_code", 0))` を追加し、recovery_mode・Task Scheduler と整合
- [ ] **P1**: `mail_pipeline.py` コアのユニットテスト追加 — `call_claude`（モック）、`classify_email_v2`（Batch モック）、`filter_engineers_by_skills`、`get_today_cost_usd`
- [ ] **P1**: 裸 `except:`（L587, L818）を `except (json.JSONDecodeError, ValueError)` に限定し、予期しない例外はログ+再 raise
- [ ] **P1**: 致命/メール単位エラーに `traceback.format_exc()` または `logging.exception` を追加
- [ ] **P2**: `raw_inbox.update_classify_result` / `count_processed` のテスト追加
- [ ] **P2**: `test_notion_engineer_payload.py` の `_make_validate_fn` を本物 `mail_pipeline.validate_engineer_payload` インポートに差し替え
- [ ] **P2**: `FETCH_LIMIT` / `PROCESS_LIMIT` を環境変数化（`RECOVERY_MODE` 非活性時の運用柔軟性）
