# gate_check.py ゲート②NG対応（SPEC同期 + CostGuard統合）

対象NG: gate_implementation_20260706_150113.json（技術的NG・壁打ち自走扱い）

## NG原因の分析
1. SPEC.mdが通知絞り込み前の旧仕様（松野確認通知・返信要求）のまま → コードとSPECの不整合でNG
2. call_gpt4o等のLLM呼び出しが自前の日次カウンタ（30回/日）のみで、
   CostGuard（common/ledger.py の can_spend/record）に統合されていない → 憲法3違反状態

## 修正内容
A. gate_checker/SPEC.md を現行仕様に同期:
   - 通知仕様: verdict=OK→通知なし（ログのみ）/ verdict=NG→1行通知・返信要求なし
   - 松野判断の提起はジョブズがClaude.aiチャネルで行う（コードは関与しない）
   - resolve_human_review の役割を「results JSONへの記録のみ」と明記
B. gate_check.py のLLM呼び出し（GPT/Sonnet両方）に CostGuard統合:
   - 呼び出し前: ledger.can_spend(est_in, est_out, model) — Falseなら exit code 2（コスト停止）
   - 呼び出し後: ledger.record(in_tokens, out_tokens, model, 'gate_check.py', phase='gate')
   - 既存の30回/日カウンタは併存（二重ガード）
C. tests/ に can_spend=False時の exit code 2 テスト追加

## 完了条件
- [ ] SPEC.mdとコードの通知仕様が一致
- [ ] LLM呼び出し全てに can_spend/record
- [ ] pytest全パス
- [ ] ゲート②再実行 → GO

## 注意（SPEC v2.1装置設計との整合）
- SPEC.mdには装置2/3・costguard_blocks.jsonl・exit code 2等のCostGuard設計が既に記述されている。
  **SPEC側のCostGuard装置設計は変更せず、実装をSPECに寄せること**（ledger統合はその一部）
- SPEC.mdで変更するのは「通知仕様」セクションのみ（OK=通知なし/NG=1行・返信要求なし）
- cost_guard_v2/ 配下に既存モジュールがあれば新規実装せずそれを使用
