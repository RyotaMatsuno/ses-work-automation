# SPEC_session_v2.md - セッション保存＋チャンネルID自動取得
# 作成: 2026-05-25

## 変更概要
save_session.py にチャンネルID自動取得を追加する。

## save_session.py への追加仕様
ログイン＋Cookie保存の後、以下を追加：
1. https://developers.line.biz/console/ のチャンネル一覧ページを開く
2. ページ内のチャンネル一覧からチャンネル名とチャンネルIDを全件取得
3. 取得結果を okamoto_channels.json に保存（同ディレクトリ）
4. 標準出力に "CHANNELS_SAVED: {件数}件" と各チャンネル名・IDを出力

## チャンネルIDの取得方法
- コンソールのURL構造: /console/channel/{channel_id}/
- チャンネル一覧ページ上のリンクhrefからIDを正規表現で抽出
- チャンネル名はリンクのテキストから取得
- 取得できない場合は "CHANNELS_NOT_FOUND" を出力（エラー終了はしない）

## 保存ファイル
- okamoto_channels.json: [{name: "チャンネル名", id: "チャンネルID"}, ...]

## 変更対象ファイル
- save_session.py のみ修正（use_session.py は変更不要）
