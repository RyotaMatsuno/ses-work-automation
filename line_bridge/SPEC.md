# SPEC.md ｜ LINE指示橋＋AI作業キュー

## 1. 概要
LINEを松野の指示入口にする。ルーターがメッセージを種別判定し、即時系/重作業系に振り分ける。

## 2. コンポーネント
- ルーター：既存LINE Webhook（line_webhook / Cloud Run）に種別判定を追加
- 作業キュー：Notion新規DB「AI作業キュー」
- ワーカー：matching_v3 / ジョブズ / ジラード / 渋沢 / Cursor / Claude Code / Codex
- 結果返却：LINEへ通知（reply優先、push節約）

## 3. ルーティングロジック
- 案件文/スキルシート転送・照会コマンド（「今日の案件」「この人どう」）→ 即時系 → matching_v3 → reply即返答
- 「重作業に回して」「深掘り」「提案文まで」等の営業重作業 → キュー登録（種別=営業, 担当=girard）
- 請求/入金/契約マスター/試算/節税系 → キュー登録（担当=shibusawa）。出番は成約以降
- 「CostGuard見て」等の開発系 → キュー登録（担当=cursor/codex）
- 送信/請求/契約/本番DB更新を含む依頼 → キュー登録＋人間確認=要（自動実行しない）
- 判定が曖昧 → 松野に1問だけ確認（種別の選択肢をreplyで提示）
  - 停止条件: 確認reply後も判定不能の場合は「判定できないためキュー未登録」とreplyし処理終了（最大1往復で打ち切り、無限ループ禁止）

## 4. 作業キューDB（Notionスキーマ）
task_id / 受付元(LINE/jobz/cursor) / 種別(matching/proposal/contract/billing/eval/dev/research) / 優先度(緊急/高/中/低) / 締切(即時/今日中/今週中) / 入力データ / 使用許可(read-only/draft-only/write) / 担当(matching_v3/jobz/girard/shibusawa/cursor/claude-code/codex) / 状態(queued/running/review/done/blocked) / コスト見込み / 結果リンク / 人間確認(要/不要) / 作成日時 / 完了日時

## 5. 状態遷移
queued → running → (review：人間確認要のとき) → done ／ 失敗時 blocked（理由記録）

## 6. 既存資産との接続
- LINE Webhook：既存line_webhookに追加。担当者判定はuser_id（松野: Ue3508b43b84991f5a68281da5bf4cf39）
- matching_v3：即時系はそのまま呼ぶ（判定はルールベース＝APIゼロ）
- Notion：作業キューDBを新設。REST API直叩き（MCPはタイムアウトするため）

## 7. 制約
- LINE：reply APIは無制限／push（プロアクティブ通知）は月200通上限
  → 非同期完了通知はpushを食う。日次ダイジェスト or 松野が「進捗」コマンド→replyで返す設計を優先
- CostGuard：ルーター・ワーカーすべて上限下。matching_v3はAPIゼロ。構造化/提案文ドラフトはLLM→CostGuard必須
- 作業キューDBは肥大化防止のためdone/blockedを定期失効（6/2のDB膨張の轍を踏まない）

## 8. 並列処理設計（2026-06-09 追加）

### 要件
- キューに積まれたタスクを詰まらせず全件並行処理する
- 手動操作ゼロ（Cloud Schedulerが5分おきに自動トリガー）
- CostGuardはバッチ件数上限を撤廃し、日次/月次コスト上限のみで管理

### 実装方針
- `pickup_and_run()` をThreadPoolExecutor で並列化（max_workers=5）
- 1タスク = 1スレッド。スレッド間は独立（ロック解放）
- _PICKUP_LOCK は廃止（スレッド単位でqueued→runningのCAS的更新で競合防止）
- 各スレッドが Notion で `状態=running` に更新してから処理開始。
  別スレッドが同じタスクを取らないよう running 更新後に latest を再取得して確認（既存ロジック流用）
- CostGuard.begin_batch / end_batch の batch_limit チェックを撤廃。
  代わりに reserve() 内の日次/月次チェックのみで制御。
  コスト上限到達時は CostLimitError を raise → そのタスクだけ blocked に落とす

### Cloud Scheduler設定
- ジョブ名: line-bridge-worker-cron
- スケジュール: */5 * * * *（5分おき）
- ターゲット: POST https://line-webhook-74735301292.asia-northeast1.run.app/line-bridge/worker
- ヘッダー: X-Line-Bridge-Token: jobz-bridge-2026
- リージョン: asia-northeast1

### Cloud Run設定変更
- --max-instances=5（並列リクエスト対応）
- --timeout=120（タスク処理時間を考慮）
- --concurrency=1（1インスタンスに1リクエスト、複数インスタンスで並列）
