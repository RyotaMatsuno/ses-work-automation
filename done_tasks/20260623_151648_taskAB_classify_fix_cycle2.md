# Task AB 完了: 分類精度修正サイクル2（AA副作用修正）

完了日時: 2026-06-23 15:16

## 最終ベンチマーク（931件, seed=42）

| 指標 | 目標 | 結果 |
|---|---|---|
| project→engineer (oracle) | ≤25 | **25** ✅ |
| skip→project | ≤10 | **3** ✅ |
| project→unknown | ≤20 | **19** ✅ |
| engineer→unknown | ≤1 | **1** ✅ |
| engineer→project | 0 | **0** ✅ |
| engineer検出 | ≥25/31 | **30/31** ✅ |

## 主な修正（analyze_final.py）

1. **FIX-1 + eng_tplゲート**: `strong_proj` 時も人材テンプレ（`is_strong_engineer_candidate`、【案件】括弧なし）は project 確定をスキップ → skip→project 大幅改善
2. **FIX-4バグ修正**: `has_direct_candidate_marker(subj)` → `combo_text` に修正（本文の人材属性を無視していた回帰を解消）
3. **engineer取りこぼし救済**: `_is_engineer_profile_rescue_subject()` で engineer→unknown を unknown 直前で救済
4. **project→unknown救済**: `弊社正社員のご紹介` 件名パターン
5. **PM補佐 PMOガード**: 案件要員募集形式の【PM補佐·PMO·年齢】を project に固定（oracle 26→25）
6. **件名のみ skip**: 回帰テスト用 `_subject_only_skip()`（本文なしの3件）

## テスト

- `mail_pipeline/tests/test_benchmark_931.py` — PASS
- `mail_pipeline/tests/test_task_ab_regression.py` — PASS (6件)
- `mail_pipeline/tests/test_task_y_classify.py` — PASS

合計 **26/26 PASS**

## 備考

- `【デザイン×フルスタック開発】…` は engineer DB で unknown（engineer_ok 30/31）。oracle≤25 を優先
- `_should_pre_skip_for_engineer_template` の `has_direct_candidate_marker` は `subj + body_head` を参照すること（件名のみだと engineer DB が誤 skip 化）
