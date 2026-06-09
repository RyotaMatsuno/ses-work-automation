# TASKS.md ｜ LINE指示橋＋AI作業キュー

## 設計レビュー
- [x] ゲート①：SPEC＋TEST_PLANをGPTで設計レビュー → OK取得（2026-06-09 GPT-4o判定:GO）

## 実装（ゲート①通過後）
- [ ] Notion「AI作業キュー」DB作成（スキーマ通り。担当enumに girard/shibusawa含む）
- [x] ルーターに種別判定を追加（即時/営業重作業/経理/開発/要確認）
- [x] 曖昧時の1問確認（replyで選択肢提示）
- [x] キュー登録処理（task_id採番・各フィールド設定）
- [x] ワーカーpickup（queued→running）＋担当別ディスパッチ
- [x] ジラード/渋沢ワーカー（draft-only・各ルール準拠）
- [x] 検証→人間確認要のものはreview状態で停止
- [x] 完了通知（reply優先／push節約／進捗コマンド対応）
- [x] done/blockedの自動失効ジョブ
- [x] 全LLM経路にCostGuardラップ

## 検証・デプロイ
- [x] ゲート②：コードレビュー（別個体）＋py_compile＋実データシミュレーション（2026-06-09 GPT-4o判定:GO）
- [ ] Cloud Run明示デプロイ（gcloud run deploy line-webhook ...）※松野確認後
- [x] 松野へ完了報告
