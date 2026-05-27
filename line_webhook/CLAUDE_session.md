# CLAUDE.md - LINE Developer Consoleセッション保存
# 作成: 2026-05-25

## 目的
岡本のLINE Developersコンソールにブラウザ自動操作でログイン済み状態を維持する。
Cookieをファイルに保存し、次回以降はCookieを使ってCAPTCHAをスキップする。

## 禁止事項
- パスワードをコード内にハードコードしない（.envから読む）
- Cookieファイルをgitにコミットしない
- Cookieファイルをログに出力しない

## 制約
- Python + Playwright (playwright-python) を使用
- 保存先: ses_work/line_webhook/okamoto_session.json
- .envパス: C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env
- 200行以内

## 完了条件
- py_compile 通過
- TASKS.md 全チェック完了
