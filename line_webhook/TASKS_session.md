# TASKS.md - LINE Developerセッション保存スクリプト
# 作成: 2026-05-25

## Task 1: save_session.py 作成
- [ ] headed Playwrightブラウザ起動
- [ ] LINE Developersログインページを開く
- [ ] input()で岡本の手動ログイン完了待ち
- [ ] Cookie → okamoto_session.json に保存
- [ ] py_compile 通過

## Task 2: use_session.py 作成
- [ ] okamoto_session.json 読み込み
- [ ] headlessブラウザにCookieセット
- [ ] コンソールページ遷移・ログイン確認
- [ ] SESSION_EXPIREDハンドリング
- [ ] --channel-id / --webhook-url 引数でWebhook設定
- [ ] 結果を標準出力
- [ ] py_compile 通過

## Task 3: 完了報告
- [ ] 変更ファイル一覧と動作確認コマンドを出力
