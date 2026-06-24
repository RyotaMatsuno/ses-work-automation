# SES自動化システム 大規模監査レポート
日時: 2026-06-24
調査者: ジョブズ + GPT-5.4壁打ち2回
調査範囲: CostGuard, matching_v3, mail_pipeline, Notion DB, スケジューラ, secrets, git, LINE, 排他制御

## 発見数サマリー
- P0（即日対応）: 7件
- P1（今週対応）: 8件
- P2（来週以降）: 5件
- GPT壁打ち: 2回実施、追加指摘6件をP0/P1に反映済み

## P0 一覧（即日対応）

### P0-1: .envがOneDrive同期対象（22件のAPIキー・パスワード露出）
- config/.envがses_work/配下にあり、OneDrive経由でクラウドストレージに全秘密情報が保存
- 含まれるキー: Notion, LINE(松野/岡本), Anthropic, OpenAI, Gemini, Firecrawl, freee, メールPW×3, jobz認証
- 対策: AppData/Local/ses_work/secrets/へ移設 + 全キーローテーション

### P0-2: git未コミット6,518件（コード消失リスク）
- ses_work全体がほぼ未コミット
- PC故障・OneDrive障害で全コード喪失
- 対策: .gitignore整理→snapshot commit→private remoteへpush

### P0-3: CostGuard二重管理（$8上限が機能していない）
- cost_guard.py main(): HARD_DAILY=$20, MONTHLY=$300（ハードコード）
- .env/common/ledger.py: DAILY=$8, MONTHLY=$140
- cost_log.jsonl vs state.sqlite3の二重帳簿（今月差額$2）
- 対策: v1 main()廃止→v2(ledger)に統一、state.sqlite3を正本化

### P0-4: Notion案件DB スキーマ不整合（全案件400エラー）
- matching_status/realtime_match_count が案件DBに存在しない
- matching_v3実行の都度、全案件でNotion 400発生（40件+/日）
- 対策: まずコード側で書き込み停止→必要性確認後にDBプロパティ追加

### P0-5: cost_guard_state.json がOneDrive上
- 行動憲法§25「AppData/Local」に反してses_work/直下
- OneDrive同期競合で状態破損リスク
- 対策: P0-3のCostGuard統一と同時にAppData/Localへ統合

### P0-6: LINE月次push残0通
- 月200通上限到達済み、reply-onlyモード
- 新規push通知が一切出せない
- 対策: 有料プラン移行 or 代替通知（メール/Notion）への切替判断

### P0-7: 実行経路の不明確さ（GPT指摘）
- 有効/無効タスクが混在（19タスク中5件無効）
- 50個以上のバッチファイルで現役/死蔵が不明
- cost_guardが3実装並存（root/matching_v3/common）
- 対策: タスク棚卸し→本番経路確定→不要タスク削除

## P1 一覧（今週対応）

### P1-1: DAILY_CALL_LIMITが業務を大量ブロック
- stopped_call_limit: 2,261件蓄積
- 6/22: classify 605件, matching 134件ブロック
- 6/19: classify 945件, matching 272件ブロック
- 対策: 「破棄→キュー保留」への設計変更 + 前段フィルタ効率化

### P1-2: SES_MatchingV3タスク無効
- 旧タスクSES_MatchingV3は無効（最終実行6/17）
- jobz_matching_dailyが代替（8:00設定だが今日は12:09に遅延実行）
- 対策: 旧タスク削除、新タスクの実行確認

### P1-3: 排他制御の未統一
- matching_v3, mail_pipeline: LockFile/lock機構あり ✓
- cost_guard, outlook, realtime_worker: 排他制御なし ⚠️
- 対策: 全ジョブに統一LockFile方式を適用

### P1-4: match_results.jsonlにタイムスタンプなし
- 118,107レコード中タイムスタンプフィールドなし
- 日別・バッチ別の追跡不能
- 対策: timestamp/run_idフィールド追加

### P1-5: エンジニア35名（17%）が単価未設定で除外
- 208名中35名が死蔵
- データ入力不備だが売上機会損失
- 対策: 入力不備アラート + 暫定推定単価の検討

### P1-6: バッチファイル50件超の混在
- Codex時代旧バッチ、matching_v2バッチ、重複freeeバッチ等
- 対策: 棚卸し→現役限定（5-10本）→旧版legacy/隔離

### P1-7: matching_v3/cost_guard.py独自上限
- DAILY_CALL_LIMIT=1500, DAILY_COST_LIMIT=$1.00（root CostGuardと別系統）
- 対策: P0-3のCostGuard統一で解消

### P1-8: 監査ログの真正性不足（GPT指摘）
- cost_log.jsonlにmodel="model"のゴースト記録
- タイムスタンプ・run_id不足
- 対策: ログスキーマ固定+バリデーション

## P2 一覧（来週以降）

### P2-1: pipeline.logにバックログ39件
### P2-2: structured.jsonlに今日分なし
### P2-3: mail_pipelineログファイル不在（pipeline.logで代替）
### P2-4: TERRA_Monthly_Invoiceの前回実行1999/11/30
### P2-5: Notion schema validation（circuit breaker）不在

## コスト状況
| 期間 | ledger DB | cost_log.jsonl | 上限 |
|---|---|---|---|
| 今日 | $0.26 | $0.05 | $8.00 |
| 6月計 | $14.38 | $12.44 | $140.00 |

## システム稼働状況
| システム | 状態 | 備考 |
|---|---|---|
| jobz-command | ✅ 稼働 | |
| mail_pipeline | ✅ 稼働 | v6.0, backlog 39件 |
| matching_v3 | ⚠️ 動作するがNotion 400 | 全案件で書き込み失敗 |
| SES_CostGuard | ⚠️ ハードコード値使用 | $8上限が$20に |
| LINE push | ❌ 残0通 | reply-onlyモード |
| SES_MatchingV3 | ❌ 無効 | jobz_matching_dailyが代替 |
| freee_auto_invoice | ❌ 無効 | |

## GPT-5.4 合意事項
1. v1 main()は廃止してv2に統一（恒久策としてラッパー不可）
2. state.sqlite3を正本、cost_log.jsonlは監査ログとして分離
3. Notionスキーマ追加よりコード側の書き込み停止が先
4. 秘密情報のOneDrive退避が最優先
5. DAILY_CALL_LIMITは「破棄→保留キュー化」が先

## 推奨実行順序
### 今日
1. .env移設 + キーローテーション開始
2. .gitignore整理 + snapshot commit
3. LINE代替通知 or 有料化判断

### 今週（Cursorタスク）
4. CostGuard統一（v1廃止→v2一本化）
5. Notion書き込み停止（matching_status/realtime_match_count）
6. DAILY_CALL_LIMIT「破棄→保留」設計変更
7. 排他制御統一
8. バッチ棚卸し

### 来週
9. バッチ統廃合
10. 通知設計見直し
11. CI/CD・監視整備
