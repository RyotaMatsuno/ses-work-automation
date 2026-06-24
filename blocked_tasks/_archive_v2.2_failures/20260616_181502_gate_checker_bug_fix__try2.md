# 【Cursor作業指示】gate_checker 本体バグ修正

対象ディレクトリ: ses_work/gate_checker/

## 背景
2026-06-16のcost_guard_v2 SPEC v2.0レビューで以下が発覚:
- GPT-4o が実SPECを読まず、テンプレ的内容でハルシネーション
- Gemini側は ERROR でフォールバック(片肺)
- 形式上 GO 判定だが信頼不能

## 作業内容
gate_checker/ の本体を点検し、以下を修正:

1. **GPT-4o入力のハルシネーション原因特定**
   - 実SPECファイル内容がプロンプトに正しく埋め込まれているか確認
   - max_tokens / context window 設定の妥当性確認
2. **Gemini フォールバック失敗原因特定**
   - エラーログの確認
   - リトライ/タイムアウト設定の妥当性確認
3. **agreement_checker の挙動確認**
   - 片肺(片方ERROR)時の判定ロジックを「条件付きGO以下」に変更
4. **回帰テスト追加**
   - tests/test_gate_checker_input_consistency.py 新規作成
   - SPECファイル内容がプロンプトに含まれることを検証

## 完了条件
- 修正後の gate_checker で cost_guard_v2 SPEC v2.2 を再レビュー
- GPT-4o と Gemini 両方から実SPEC内容を踏まえたレビューが返ってくること
- 片肺時は自動的に「条件付きGO以下」判定になること

## 注意事項
- 暫定運用: 修正完了まで素OpenAI API + gpt-5.4(reasoning_effort=low / max_completion_tokens=8000) を使用
- 修正完了をジョブズに報告すれば暫定運用を終了する


## RETRY 1 REASON
target_file not found: 


## RETRY 2 REASON
target_file not found: 


## BLOCKED REASON
target_file not found: 
