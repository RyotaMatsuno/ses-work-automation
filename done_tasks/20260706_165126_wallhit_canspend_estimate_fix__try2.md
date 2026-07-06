# wall_hitting.py can_spend見積もり修正（GPT-5.4壁打ち指摘・即時対応）

根拠: research_results/gate_hardening_backlog_20260706.md / 壁打ち判定「②のみ即修正、他はバックログ妥当」
問題: can_spend(300, 500, model) の固定推定は事前ブロックの入口として過小。
recordは実トークンで正確だが「1発超過」を防げない（6/2の$50暴走前歴あり）。

## 修正内容（wall_hitting.py）
1. est_in を実プロンプト長から動的算出: est_in = max(500, len(プロンプト全文) // 3)
2. est_out = 各呼び出しのmax_tokens設定値をそのまま使用（固定500をやめる）
3. search系モデル（gpt-4o-search-preview等、モデル名に 'search' を含む）は
   est_in/est_out とも1.5倍の保守係数をかける
4. ledger単価表に存在しないモデル名の場合はWARNINGログ + 保守係数2倍で見積もる
5. can_spend Falseの場合の挙動は現状維持（実行せずexit）

## テスト（tests/test_wall_hitting_record.py に追加）
- 推定値が入力長に連動すること
- searchモデルで1.5倍係数が効くこと
- can_spend呼び出し引数の検証（固定300/500が渡らないこと）

## 完了後
python gate_checker/gate_check.py --phase implementation --file wall_hitting.py
→ GO想定（残指摘は全て助言バックログ化済み）。GOが出たらこの系統は完全クローズ。

## 追加: レビュー出力の切断耐性（同時実施）
背景: agreement_checker.py のゲートで Sonnetレビューが3000トークンで途中切断され
【判定】行が欠落 → パース失敗で偽NG になった。
1. レビュープロンプト（GPT/Sonnet共通）に「**1行目に必ず【判定: GO/NG】を書き、その後に理由**」を追加
2. パーサーは先頭・末尾どちらの判定行も受理するよう修正
3. SONNET_MAX_TOKENSは3000のまま（切断されてもverdictが取れる設計を優先）
4. 完了後: agreement_checker.py も再ゲート
   python gate_checker/gate_check.py --phase implementation --file gate_checker/agreement_checker.py

## クローズ基準（本系統の終了条件）
- wall_hitting.py: ゲートGO
- agreement_checker.py: ゲートGO
- gate_check.py: SPEC v2.x未実装項目（装置2/3・phase_models）由来のNGは既知バックログとして
  research_results/gate_hardening_backlog_20260706.md に記録済みのためクローズ扱い（追わない）


## RETRY 1 REASON
target_file not found: 


## RETRY 2 REASON
target_file not found: 
