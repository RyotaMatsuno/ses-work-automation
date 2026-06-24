# Task AC 完了: 分類精度サイクル3（skip→project修正+回帰テスト強化）

完了日時: 2026-06-23 17:05

## 最終ベンチマーク（931件, seed=42）

| 指標 | 目標 | 結果 |
|---|---|---|
| skip→project | ≤20 | **3** ✅ |
| project→engineer (raw) | ≤32維持 | **28** ✅ |
| project→engineer (oracle) | — | 19 |
| project→unknown | 増やさない | **19** ✅ |
| engineer→unknown | 増やさない | **0** ✅ |
| engineer検出 | ≥25/31 | **27/31** ✅ |

## 主な修正（analyze_final.py）

1. **`_HUMAN_ONLY_SIGNALS` + `has_human_only_signal()`** — 弊社正社員のご紹介、注力要員、26歳/男性、弊社フリーランス等の人材専用語で pre-skip 強制
2. **pre-skip ゲート強化** — `strong_proj` より前に human_only 判定。案件語があっても人材専用語優先で skip
3. **engineer 除外** — `has_engineer_headline` / `_is_clear_engineer_intro` がある場合は human_only skip を抑止（★新着★直個人等の誤 skip 防止）
4. **AB 救済削除** — `弊社正社員のご紹介` → project 固定を削除（skip 人材の誤 project 化の原因）

## テスト

- `mail_pipeline/tests/test_task_ac_regression.py` — 新規 (4件)
- `mail_pipeline/tests/test_benchmark_931.py` — AC目標に更新（skip≤20, pe raw≤32）
- 既存 AB/Y テスト — PASS

合計 **30/30 PASS**
