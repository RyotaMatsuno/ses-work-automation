# gate_checker仕上げ: wall_hitting record追加 + Sonnetタイムアウト修正

対象NG: gate_implementation_20260706_161811.json（残指摘は wall_hitting被覆のみ。他は全クリア）

## 1. wall_hitting.py の CostGuard 完全被覆
- 現状: can_spend は L180-181 で実装済み / **ledger.record が未実装（片肺）**
- 修正: 各LLM呼び出し成功後に ledger.record(in_tokens, out_tokens, model, 'wall_hitting.py', phase='wallhit') を追加
  （API responseのusageから実トークン取得。取得不能時は推定値で記録）
- テスト: recordがモックで1回呼ばれることを確認するユニットテスト追加

## 2. SPEC.md §7 更新
- 「wall_hitting.py 呼び出しはWeek2でCostGuard被覆を確認する（未確認）」の記述を
  「確認済み: can_spend（呼び出し前）+ record（成功後）被覆完了（2026-07-06）」に更新
- 変更履歴に v2.4 として1行追記

## 3. agreement_checker.py Sonnetタイムアウト修正
- TIMEOUT_SECONDS: 45 → 90（L55）
- 根拠: SONNET_MAX_TOKENS=3000 の生成に45秒では不足し、本日4連続タイムアウト。
  GPT/Sonnetは並列実行のためゲート全体は 90秒+α でMCP制限120秒内に収まる
- 注意: リトライ設計（attempt 2回）と組み合わせて最悪 90×2=180秒 にならないよう、
  **タイムアウト起因の失敗はリトライしない**（1発で諦めてERROR返却）に変更

## 4. ゲート②再実行（--dirは使わない。62Kトークンになるため）
python gate_checker/gate_check.py --phase implementation --file gate_checker/gate_check.py
python gate_checker/gate_check.py --phase implementation --file gate_checker/agreement_checker.py
python gate_checker/gate_check.py --phase implementation --file wall_hitting.py

## 完了条件
- [ ] wall_hitting.py に record 追加 + テストパス
- [ ] SPEC §7 更新（v2.4）
- [ ] TIMEOUT_SECONDS=90 + タイムアウト時リトライなし
- [ ] 上記3ファイルのゲート② GO（Sonnetがタイムアウトせず応答すること）


## RETRY 1 REASON
Claude Code TIMEOUT


## RETRY 2 REASON
target_file not found: 
