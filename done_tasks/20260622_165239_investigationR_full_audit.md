# 【Cursor作業指示】Investigation R: 全システム徹底調査

対象ディレクトリ: ses_work/ (全体)
作業内容: 全コードベースの徹底調査 → バグ・リスク・改善点の洗い出し
完了条件: INVESTIGATION_REPORT.md を ses_work/ に出力
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 目的

SES自動化システム全体を徹底的に調査し、以下を洗い出す:
1. 潜在バグ（サイレント障害・エッジケース・競合状態）
2. セキュリティリスク（API鍵露出・インジェクション・権限）
3. データ整合性問題（DB不整合・Notion乖離・重複）
4. パフォーマンス問題（N+1・メモリリーク・タイムアウト）
5. コード品質（デッドコード・重複実装・型安全性）
6. 運用リスク（単一障害点・復旧手順不備・監視欠如）

## 現状データ

### raw_inbox.db
- Total: 5495 / Processed: 4995 / Unprocessed: 500
- 分類内訳: {'migrated': 1560, 'skip': 1446, 'other': 1087, 'project': 896, None: 467, 'person': 14, '人材': 5, 'candidate': 4, 'event': 3, '人材情報': 2, 'talent': 2, 'resource': 2, 'recruitment': 2, '人材紹介': 1, 'service': 1, 'proposal': 1, 'offer': 1, 'individual': 1}

### システムファイル
  mail_pipeline/mail_pipeline.py: 2111L (06/22 16:51)
  mail_pipeline/raw_inbox.py: 486L (06/22 12:57)
  analyze_final.py: 277L (06/22 15:01)
  cost_guard.py: 907L (06/22 12:57)
  common/ledger.py: 568L (06/22 12:57)
  matching_v3/matching_v3.py: 336L (06/22 12:57)
  matching_v3/skill_judge.py: 255L (06/19 12:17)
  line_webhook/webhook_server.py: 2503L (06/19 18:04)
  line_webhook/matching_logic.py: 291L (06/19 17:43)
  line_webhook/skill_utils.py: 76L (06/19 18:01)
  line_query/line_query.py: 609L (06/19 18:04)
  nightly_jobz/nightly_jobz.py: 215L (06/22 12:57)
  nightly_jobz/task_processor.py: 247L (06/22 12:57)
  nightly_jobz/config.py: 58L (06/22 12:57)
  gate_checker/gate_check.py: 814L (06/22 12:57)
  freee/freee_invoice_v2.py: 483L (06/22 12:57)
  local_server/command_server.py: 364L (06/22 12:57)

---

## 調査項目（必ず全項目を実施すること）

### A. mail_pipeline 徹底調査

#### A1. 分類精度
- analyze_final.py の全パターンを読み、誤検知しうるパターンを列挙
- classify_by_rule のスコアリングでエッジケースを特定
- BODY_ENGINEER_STRONG / BODY_PROJECT_STRONG の網羅性を検証
- PROJECT_OVERRIDE_RE が必要十分か検証

#### A2. 抽出精度
- classify_email (AI抽出) のプロンプトを読み、抽出漏れパターンを特定
- price_extractor.py / skill_extractor.py が存在すれば、ルール網羅性を検証
- Notion登録時のプロパティマッピングが正しいか全フィールド確認

#### A3. DB整合性
- raw_inbox.db のスキーマとindex確認
- processed=1 なのに classify_result がNone のレコード
- message_id の重複チェック
- retry_count が異常に高いレコード

#### A4. IMAP取得
- fetch_recent_emails のエラーハンドリング
- タイムアウト処理の妥当性
- アカウント切替ロジック（matsuno/okamoto/sessales）

#### A5. CostGuard統合
- cost_guard.py + common/ledger.py の全エントリポイントを追跡
- allowed() / finalize() が全てのLLM呼び出しで使われているか
- fail-close が正しく機能するか（ファイル読み込み失敗時の挙動）
- phase_threshold と call_limit の値が config/.env と一致するか

### B. マッチング徹底調査

#### B1. webhook_server.py
- run_reverse_matching のスコアリングロジック全行レビュー
- skill_utils.py のnormalize_skill / skill_match のエッジケース
- 価格が0/None/異常値の場合の挙動
- stats の計算が正しいか

#### B2. line_query.py
- handle_line_query の全フロー追跡
- Notionクエリのフィルタが正しいか（ステータス、鮮度）
- #skill_skip の適用タイミング
- 勤務地フィルタの有無と影響

#### B3. matching_v3.py
- 自動マッチングの全フロー
- skill_judge.py のAI呼び出しとCostGuard統合
- weekday_guard の曜日判定
- LINE通知のフォーマットと上限管理

#### B4. マッチング結果品質
- raw_inbox.db から50件のproject emailをランダム取得
- 各メールに対してanalyze_final.classify_by_rule を実行し分類精度を計測
- 誤分類パターンを列挙

### C. nightly_jobz 調査

#### C1. Phase 1 安全性
- DRY_RUN の評価タイミング（モジュールレベル定数 vs 関数呼び出し）
- ALLOW_PROD_WRITES フェイルセーフの実装
- lock ファイルのクリーンアップ（異常終了時）
- Notion キュー操作の冪等性

#### C2. 設計レビュー
- task_processor.py の各種別ハンドラ
- GPT-5.4 呼び出しのエラーハンドリング
- briefing.json の出力フォーマット

### D. freee / 請求書

#### D1. freee_invoice_v2.py
- Google Sheets読み取りの認証フロー
- freee API呼び出しのエラーハンドリング
- 源泉徴収計算（TERRA=税抜×10.21% / GL・FT=なし）
- 承認ゲートの実装

#### D2. 退役済みスクリプト
- freee_invoice_monthly.py が残存していないか
- 旧スクリプトの参照が残っていないか

### E. gate_checker

#### E1. GPT-4o + Sonnet 並列レビュー
- 両方のAPI呼び出しが正しく実装されているか
- フェーズ別モデルルーティング
- NG判定時の分岐（技術NG→壁打ち / 仕様NG→松野確認）

### F. インフラ / 運用

#### F1. jobz-command サーバー
- command_server.py のセキュリティ（認証トークン、ローカルのみ）
- 27分タイムアウトのハンドリング
- start_server.bat の自動起動

#### F2. タスクスケジューラ
- 全SES_*タスクの状態と設定確認
- 次回実行時刻の妥当性
- 失敗時のリトライ設定

#### F3. Cloud Run
- line_webhook のDockerfile確認
- 環境変数の設定漏れ
- メモリ/CPU設定の妥当性

#### F4. config/.env
- 全変数の用途と値の妥当性確認
- 未使用変数の特定
- 秘密情報の管理状態

### G. コード品質

#### G1. デッドコード
- 使われていない関数/ファイルの特定
- 旧バージョンの残骸

#### G2. エラーハンドリング
- try/except の範囲が適切か
- bare except の有無
- ログ出力の一貫性

#### G3. 型安全性
- None チェックの漏れ
- 暗黙の型変換

---

## 出力フォーマット

ses_work/INVESTIGATION_REPORT.md に以下の形式で出力:

```markdown
# 全システム徹底調査レポート
日時: YYYY-MM-DD

## サマリー
- 致命的 (P0): X件
- 重要 (P1): X件  
- 改善推奨 (P2): X件
- 情報 (P3): X件

## P0: 致命的（即時対応必要）
### [ID] タイトル
- 場所: ファイル:行番号
- 影響: 
- 再現手順:
- 推奨修正:

## P1: 重要（今週対応）
...

## P2: 改善推奨（次スプリント）
...

## P3: 情報（記録のみ）
...

## テスト実行結果
### 分類精度テスト (50件)
...

## 推奨アクション一覧（優先順）
1. ...
```

---

## 注意事項
- 実際にコードを読んで確認すること（推測で書かない）
- 50件の分類精度テストは実際にraw_inbox.dbからデータを取得して実行すること
- バグを発見した場合、修正はしない（レポートに記録するのみ）
- config/.env の秘密情報はレポートに含めない（変数名と存在確認のみ）
- 調査の過程で見つけた全ての問題を漏れなく記録すること

---

## 完了メモ（2026-06-22）

- 出力: `ses_work/INVESTIGATION_REPORT.md`
- P0: 5 / P1: 14 / P2: 15 / P3: 11
- 分類精度テスト: 50件ランダム → 42% 一致
- DB整合性: total 5495, unprocessed 500, processed+null classify 1件, dup 0
