# SPEC.md - エンジニアDB品質改善 3タスク
# 最終更新: 2026-05-24

## タスク概要
1. LINEパイプライン名前取得バグ修正（名前なし登録を防ぐ）
2. 地域フィルター追加（関東・中部以外を除外）
3. 岡本WebhookのURL設定

---

## タスク1: LINEパイプライン 名前取得バグ修正

### 対象ファイル
- `ses_work/line_webhook/webhook_server.py`

### 問題
LINE経由で自動登録されたエンジニアで、名前が `(no name)` になるケースがある。
メッセージ解析で名前が取れない場合でも Notion に登録してしまっている。

### 修正仕様
- 名前パース後に名前が空 or `(no name)` の場合:
  1. Notionへの登録を**スキップ**する
  2. LINE返信で「名前が取得できませんでした。「氏名: 〇〇」の形式で再送してください。」と返す
  3. ログに `[SKIP] name not found: {元メッセージ冒頭100文字}` を出力する

### 確認方法
- py_compile で構文チェックのみ（本番テストはJobzが別途実施）

---

## タスク2: エンジニアDB 地域フィルター

### 対象ファイル
- `ses_work/line_webhook/webhook_server.py`（登録時）
- `ses_work/matching_v2/matching_v2.py`（マッチング時）

### 除外ルール
- **除外**: 関東・中部以外の地域の人材
- **関東**: 東京都、神奈川県、埼玉県、千葉県、茨城県、栃木県、群馬県
- **中部**: 愛知県、岐阜県、三重県、静岡県、長野県、富山県、石川県、福井県、山梨県、新潟県
- **判定方法**: 最寄り駅 or 居住地のフィールドから都道府県を判定
  - フィールド名: `備考（LINEメモ）` または スキルシート記載の最寄り駅テキスト

### webhook_server.py への追加
- エンジニア登録時、最寄り駅/居住地から都道府県を判定
- 関東・中部以外 → スキップ + LINE返信「対応エリア外のため登録をスキップしました（関東・中部のみ対応）」
- 判定できない場合 → 登録する（不明は通す）

### matching_v2.py への追加
- エンジニアDBから取得後、居住地・最寄り駅が明確に関東・中部以外の場合は候補から除外
- 判定はNotionの「備考（LINEメモ）」または将来的に追加する「居住エリア」フィールドから行う
- 現時点では **matching_v2.pyへの変更は不要**（登録時点で弾けば十分）
- → **タスク2はwebhook_server.pyのみ修正**

### 確認方法
- py_compile で構文チェックのみ

---

## タスク3: 岡本Webhook URL設定

### 背景
岡本の LINE公式アカウントのWebhook URLが未設定。
Cloud RunのWebhookサーバーはすでに `webhook_okamoto` エンドポイントが実装済み。

### 設定値
- Webhook URL: `https://line-webhook-74735301292.asia-northeast1.run.app/webhook_okamoto`
- チャンネルシークレット: `756a1484e20203ed23dfac88853f63a7`
- チャンネルアクセストークン: （memory参照）

### 作業
- `ses_work/line_webhook/webhook_server.py` に岡本チャンネルの認証情報が設定されているか確認
- 設定されていなければ追加（環境変数またはハードコード）
- `ses_work/config/.env` に `LINE_OKAMOTO_CHANNEL_SECRET` と `LINE_OKAMOTO_CHANNEL_TOKEN` が存在するか確認
- なければ追記

### 確認方法
- .envファイルの内容確認
- webhook_server.py の岡本ルート確認

---

## 完了条件
- [ ] webhook_server.py: 名前なし登録スキップ実装済み
- [ ] webhook_server.py: 地域フィルター実装済み
- [ ] webhook_server.py: 岡本チャンネル認証情報設定済み
- [ ] 全ファイル py_compile 通過
- [ ] TASKS.md 全チェック完了状態に更新
