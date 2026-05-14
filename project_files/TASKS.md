# TASKS.md


## メール添付スキルシート自動取り込み（優先度: 高）
追加日: 2026-05-12
詳細: `ses_work/mail_attachment_importer/TASKS.md` 参照

### Phase 0: 環境準備
- [ ] 必要ライブラリインストール
- [ ] processed_ids.json / importer.log 初期化

### Phase 1: メール取得モジュール
- [ ] IMAP接続・添付取得（mail_fetcher.py）

### Phase 2: ファイル解析モジュール
- [ ] Excel/PDF/Word → テキスト変換（file_parser.py）

### Phase 3: Claude API抽出モジュール
- [ ] スキルシートから構造化データ抽出（ai_extractor.py）

### Phase 4: Notion登録モジュール
- [ ] 重複チェック + 登録（notion_writer.py）

### Phase 5: 統合・テスト
- [ ] importer.py 統合テスト

### Phase 6: 定期実行
- [ ] タスクスケジューラ登録（毎朝8時）

---

## エンジニアDB復元・cleanup修正（優先度: 高）
追加日: 2026-05-12

- [ ] ゴミ箱復元（restore_and_fix.py実行）← Claude Desktop再起動後に実行
- [ ] cleanup条件修正: CUTOFF = "2026-04-21"（3週間前）に変更
- [ ] cleanup_v3.py として保存

---

## 岡本 公式LINE Webhook設定（優先度: 高）
追加日: 2026-05-12

- [ ] LINE Developers → 岡本アカウント → Webhook URL登録
  URL: https://line-webhook-74735301292.asia-northeast1.run.app/webhook_okamoto
- [ ] 疎通テスト ← 岡本から松野へのアクセス許可待ち

---

## freee API連携・請求書自動化（優先度: 低）
追加日: 2026-05-12

### Phase 1: 調査・認証設定
- [ ] freee API仕様確認（OAuth2.0フロー・エンドポイント）
- [ ] freee開発者アカウント・アプリ登録（松野が実施）
- [ ] OAuth認証フロー実装（アクセストークン取得・リフレッシュ）
- [ ] 接続テスト（会社情報取得API）

### Phase 2: 請求書自動生成
- [ ] 請求書テンプレート設計（Notion案件DBから情報取得）
- [ ] freee請求書作成API実装
- [ ] 取引先マスタ連携（freee ↔ Notion）
- [ ] 請求書PDF生成・確認フロー

### Phase 3: 送付・入金確認自動化
- [ ] 請求書メール送付自動化（ses-mail連携）
- [ ] 入金確認APIポーリング実装
- [ ] 入金確認通知（LINE or メール）
- [ ] 月次レポート自動生成

### 前提条件
- freee有料プランが必要（スタータープラン以上）
- API利用には freee開発者登録が必要（松野が手動対応）
