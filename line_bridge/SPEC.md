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
