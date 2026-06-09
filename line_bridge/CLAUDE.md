# CLAUDE.md ｜ LINE指示橋＋AI作業キュー

## 目的
松野がLINEからタスクを投げ込めるようにする。即時系はmatching_v3で秒返答、重作業系はNotion作業キューに積んで裏でワーカー（ジョブズ/ジラード/渋沢/Cursor/Claude Code/Codex）が処理→LINEに結果通知。

## 禁止事項
- 送信・freee確定・本番DB更新・Cloud Runデプロイを自動実行しない（人間確認ゲート必須）
- FETCH_LIMIT/batch_size/cron頻度/max_resultsを無断で増やさない
- CostGuardを通らないLLM呼び出しを作らない
- 作業キューDBを無制限に増やさない（done/blockedは自動失効）
- 同一Notionレコードを複数ワーカーで同時更新しない

## 必須
- 全LLM呼び出しはCostGuard下（日次/月次/バッチ上限）
- ジラード/渋沢は draft-only
- 既存LINE Webhook（line_webhook / Cloud Run, asia-northeast1）に追加実装。git pushでは自動デプロイされない→明示deploy
- 実装はゲート①（GPT設計レビュー）通過後に着手

## トークン経済ルール
- 各人格は自分のドメイン資料だけ読む（全PJファイルを全員に積まない）
- 受け渡しは要約パケットのみ（会話全文・生の思考は渡さない／返さない）
- 会話はタスク単位で短く保つ（作業キューで区切る）
- 安定資料・人格定義はprompt cachingで使い回す
- 上限はCostGuardで握る
