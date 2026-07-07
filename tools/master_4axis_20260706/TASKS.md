# TASKS.md — 報酬4軸キャップレス改定

## Phase 0: 設計

- [x] SPEC.md 作成
- [!] gate_check.py --phase design（2026-07-06 日次上限30/30到達 → 7/7以降に実行） （2026-07-07 GPT-4o判定:NG）

## Phase 1: Script A

- [x] `master_comp_engine.py` 共有モジュール
- [x] `update_master_4axis_A.py` 実行（2026-07-06 18:27完了）
  - [x] 前提条件 A54追記
  - [x] 営業報酬4軸 全面更新
  - [x] 確定事項一覧 A52追記

## Phase 2: Script B

- [x] `update_master_4axis_B.py` 実行（2026-07-06 18:27完了）
  - [x] 給与シミュレーション
  - [x] 成長モデル + 売却検討ライン
  - [x] 経常利益マトリクス
  - [x] 経常利益（実利率）
  - [x] 検算ゲート pass（3589万 ≈ 3600万±5% / 初期4名840万∈[830-880]）

## Phase 3: 完了

- [ ] gate_check.py --phase design（7/7以降）
- [ ] gate_check.py --phase implementation（7/7以降）
- [ ] push_or_log LINE通知
- [ ] pending_tasks → done_tasks 移動
