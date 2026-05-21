# TASKS.md - skill_reader 最終版

## Phase 1〜4: 完了
- [x] PDF/Word/画像スキルシート読み取り
- [x] Claude APIスキル抽出（テキスト・画像両対応）
- [x] 案件DB照合・粗利5〜12万ジャスト優先ソート
- [x] Notionエンジニアスキル欄自動更新
- [x] 意向確認メール文面自動生成（テンプレート準拠）
- [x] mail_pipeline v5（添付スキルシート自動検出・処理）
- [x] skill_reader_api.py（ローカルAPIサーバー PORT:8766）
- [x] skill_reader_line_bridge.py（LINE Webhook連携クライアント）配置済み
- [x] skill_reader_api スタートアップ登録（VBS経由、次回PC起動から自動起動）

## Phase 5: LINE統合（v13）
- [x] webhook_server.py v13: PDF/画像/ファイルメッセージ受信ハンドラー追加
- [x] git push済み（commit: e596693）
- [ ] Railway再デプロイ → **トライアル切れでデプロイ不可**

## ⚠️ 要対応
- Railway有料プラン移行（Hobbyプラン $5/月）が必要
  → Railway管理画面: https://railway.app/dashboard でUpgrade
  → 完了後: git push or Railwayダッシュボードから手動再デプロイ

## end-to-endテスト（Railway復旧後）
- [ ] LINEからPDFスキルシートを送信
- [ ] 解析結果がLINEに返ってくるか確認
- [ ] 「メール送信して xxx@yyy.com」で意向確認メールが届くか確認
