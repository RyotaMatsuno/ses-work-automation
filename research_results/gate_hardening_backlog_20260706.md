# gate_checker強化バックログ（2026-07-06 ゲート②助言事項）

出典: gate_implementation_20260706_164534.json（Sonnet NG・実害なし判定でクローズ）

## 次回wall_hitting改修時に対応
1. ~~can_spend推定値の精緻化~~ → GPT-5.4壁打ちにより即修正へ格上げ（20260706_165126_wallhit_canspend_estimate_fix.md）
2. wall_hitting.py専用SPEC.md作成（3点セット準拠化）
3. リトライ時のexception WARNINGログ追加（サイレント再試行の解消）

## gate_checker別タスク（SPEC v2.x未実装バックログ・既知）
- phase_models / 装置2・装置3 の完全実装

## 運用ルール追加（ハマりパターン辞書 追記対象）
- gate_check.py の --dir モード使用禁止（48ファイル62Kトークン化しGPT空応答/Sonnetタイムアウト）→ --file 個別指定
- Sonnet TIMEOUT_SECONDS=90・タイムアウト時リトライなし（2026-07-06確定）
- ゲート再実行の連打時は装置3の重複抑制に注意

## 本日の壁打ち記録
- GPT_WALLHIT_alias_narrowing_20260705.md / GPT_WALLHIT_final127_audit_20260706.md / 本クローズ判断

## 壁打ち判定（2026-07-06）
- クローズ提案はNG判定。②can_spend固定見積もりのみ即修正、①③④⑥⑦⑧はバックログ妥当との合意。
