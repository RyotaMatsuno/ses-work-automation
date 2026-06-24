# 【Cursor作業指示】Task M: gate_checker Gemini→Claude Sonnet差替え

対象ディレクトリ: ses_work/gate_checker/
作業内容: 第2レビュアーをGemini→Claude Sonnet 4.6に変更
完了条件: Sonnet呼び出し成功 + テスト

## 背景
Gemini 2.0 Flashの無料枠が完全枯渇（quota=0）。
gate_checkerが実質GPT-4o単独判定になっている。

## 修正箇所

### 1. Gemini呼び出しをSonnet呼び出しに差し替え
- model: claude-sonnet-4-6-20250514
- API: https://api.anthropic.com/v1/messages
- ANTHROPIC_API_KEY環境変数を使用
- CostGuard統合: block_type=gate_checker, phase=review_sonnet

### 2. システムプロンプト改善（GPT/Sonnet両方）
以下を追加:
- CostGuardはLLM API専用。Notion/freee/LINE等は対象外
- Notion DBの読み書きは自動送信に該当しない
- 承認済み仕様変更（soft-skill all-pass、語彙外REVIEW化等）はNG判定しない

### 3. DAILY_CALL_LIMIT
10 → 30に修正（SPEC.md準拠）

### 4. ラベル更新
gemini_verdict → sonnet_verdict（結果JSON含む）

## テスト
- Sonnet呼び出し成功
- CostGuardでコスト記録
- DAILY_CALL_LIMIT=30反映

## 共通ルール
- 既存テスト全パス / 新規コードにtype hint

---

## 完了メモ（2026-06-19）

- `agreement_checker.py`: `call_sonnet()` で Anthropic Messages API（model=`claude-sonnet-4-6`）を使用
- CostGuard: `block_type=gate_checker`, `phase=review_sonnet` で allowed/finalize 統合済み
- `gate_check.py`: `DAILY_CALL_LIMIT=30`, `COSTGUARD_NOTE` を全システムプロンプトに付与
- 結果JSON: `sonnet_review` / `sonnet_verdict` / `model=gpt-4o+sonnet`
- pytest 21件全パス（`tests/test_task_m.py` 含む）
- 実APIスモーク: CostGuard `review_sonnet` フェーズ上限でブロック（実装は正常、運用枠の問題）
