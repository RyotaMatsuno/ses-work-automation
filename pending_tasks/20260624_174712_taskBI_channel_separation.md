# 【Cursor作業指示】Task BI: チャネル分離方針のシステム反映

対象: ses_work/line_webhook/ + Notion AI作業キューDB
作業内容: チャネル分離方針をシステムに反映
参照ファイル: CLAUDE.md / line_webhook/line_bridge.py
完了条件: Notionキューにclaude_mobile受付元追加、引き継ぎパーサーLINE投入廃止
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 背景（2026-06-22 CEO確定方針）
- LINE = マッチング専用（line_query・マッチング結果通知・「作業進捗」コマンド）
- スマホClaude.ai = タスク指示チャネル
- 引き継ぎメッセージのLINE投入を廃止→スマホClaude.aiに統一

## 変更内容

### 1. Notion AI作業キューDB
- DB ID: 37a450ff-37c0-819a-981b-c2e06ed282bb
- 「受付元」selectプロパティに `claude_mobile` オプション追加

### 2. line_bridge.py
- 引き継ぎメッセージ（■セクション形式）のLINE受付を無効化
- LINEで送られた場合:「引き継ぎメッセージはスマホClaude.aiのPJチャットに貼ってください」とreply
- キューには登録しない

### 3. LINEコマンド整理
有効（変更なし）: マッチングクエリ / 作業進捗 / 案件進捗 / 人員進捗
廃止: 引き継ぎメッセージのパース→キュー登録

## 完了条件
- [ ] Notionキューにclaude_mobile受付元追加
- [ ] 引き継ぎメッセージLINE送信時に案内メッセージが返る
- [ ] マッチングクエリ・進捗コマンドは従来通り動作
- [ ] テスト全PASS
