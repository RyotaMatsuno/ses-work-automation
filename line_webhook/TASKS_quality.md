# TASKS.md - エンジニアDB品質改善 実装チェックリスト
# 最終更新: 2026-05-24

## Task 1: 名前なし登録スキップ（webhook_server.py）
- [x] 名前パース後に空 or "(no name)" の場合、Notion登録をスキップ
- [x] スキップ時にLINE返信「名前が取得できませんでした。「氏名: 〇〇」の形式で再送してください。」
- [x] ログ出力: `[SKIP] name not found: {メッセージ冒頭100文字}`
- [x] py_compile 通過確認

## Task 2: 地域フィルター（webhook_server.py のみ）
- [x] 関東・中部都道府県リストを定数として定義
- [x] エンジニア登録時に最寄り駅/居住地テキストから都道府県を判定する関数を追加
- [x] 対象外エリアの場合、登録スキップ + LINE返信
- [x] 判定不能な場合は登録を通す（不明は通過）
- [x] py_compile 通過確認

## Task 3: 岡本Webhook認証情報設定
- [x] config/.env に LINE_OKAMOTO_CHANNEL_SECRET / LINE_OKAMOTO_CHANNEL_TOKEN が存在するか確認
- [x] なければ追記（シークレット: REDACTED-SECRET、トークンはwebhook_server.py内から取得）
- [x] webhook_server.py の /webhook_okamoto ルートに岡本チャンネルの認証設定が適用されているか確認・修正
- [x] py_compile 通過確認

## Task 4: 完了報告
- [x] 変更ファイル一覧
- [x] 変更内容サマリー
- [x] py_compile 結果
