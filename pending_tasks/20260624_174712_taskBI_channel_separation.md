# 【Cursor作業指示】Task BI: チャネル分離（GPT-5.4 3ラウンド合意版）

対象: ses_work/line_webhook/
参照: CLAUDE.md / line_webhook/line_bridge.py
完了条件: チャネル分離の安全な段階移行完了
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 背景（2026-06-22 CEO確定方針）
- LINE = マッチング専用
- スマホClaude.ai = タスク指示チャネル
- 引き継ぎメッセージのLINE投入を廃止

## Phase 1: Notionキュー拡張 + イベント正規化

### 1-1. AI作業キューDB（37a450ff-37c0-819a-981b-c2e06ed282bb）
- source_channel: line_matsuno / line_okamoto / claude_mobile / jobz / cursor
- intent_type: matching / task / inquiry / other
- dedupe_key: メッセージIDベースの重複排除キー

### 1-2. line_bridge.pyにイベント正規化追加
```python
normalized_event = {
    "source_channel": "line_matsuno",
    "intent_type": "matching",  # or "task" / "inquiry"
    "raw_text": "...",
    "received_at": "...",
    "dedupe_key": "line_{message_id}"
}
```

## Phase 2: 段階移行（exit criteriaベース）

### Step 1: read-only（2営業日）
- 引き継ぎメッセージ（■セクション形式）を検知するがキュー登録しない
- feature flag: `LINE_HANDOVER_PARSER_MODE = "readonly"`
- 観測ログ:
  - 受信件数
  - 引き継ぎメッセージ検知件数
  - マッチングクエリ件数
  - 重複件数
- exit criteria: 想定外の検知/漏れが0件 → Step 2へ

### Step 2: 案内メッセージ（2営業日）
- 引き継ぎメッセージが来たら案内返信:「引き継ぎメッセージはスマホClaude.aiのPJチャットに貼ってください」
- feature flag: `LINE_HANDOVER_PARSER_MODE = "redirect"`
- exit criteria: ユーザー混乱なし + 取りこぼし0件 → Step 3へ

### Step 3: 完全移行
- feature flag: `LINE_HANDOVER_PARSER_MODE = "disabled"`
- 旧パーサーコードは削除しない（2週間無事故後に削除判断）

## Phase 3: 既存コマンド動作確認
LINEコマンド（変更なし）:
- マッチングクエリ（自由テキスト → line_query）
- 「作業進捗」→ 全タスク状態返却
- 「案件進捗」→ 案件DB状態
- 「人員進捗」→ エンジニアDB状態

## 完了条件
- [ ] Notionキューにsource_channel/intent_type/dedupe_key追加
- [ ] feature flag実装（readonly/redirect/disabled）
- [ ] Step 1観測ログ出力確認
- [ ] 既存LINEコマンド全動作確認
- [ ] テスト全PASS
