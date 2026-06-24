# CLAUDE.md - Phase4: matching_v3 品質・堅牢性修正

## 目的
matcher.py の粗利マイナスMATCH・未知スキル黙殺・絶対除外未実装という
金銭・コンプラに直結するバグを修正する。
あわせて cost_guard のGemini壊れたdegrade除去と sys.path 問題を修正する。

## 変更対象ファイル（ses_work/matching_v3/ 以下）
- matcher.py
- notion_client.py  
- cost_guard.py
- matching_v3.py（sys.path修正のみ）

## 絶対禁止
- notifier.py は触らない
- tests/ 以下は触らない（テストコードは変えない）
- ログファイル(.jsonl, .log, .db) は消さない
- SPEC.md以外のmarkdownファイルは変えない
