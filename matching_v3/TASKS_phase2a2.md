# Phase 2A2: スキル正規化パイプライン — TASKS.md

- [x] T1: scripts/normalize_all_skills.py 作成
  - get_all_engineers() で全件取得
  - skill_aliases.json で正規化
  - dry-run / apply モード
  - レポート: research_results/skill_normalize_report.md

- [x] T2: テスト追加 (tests/test_skill_normalize.py)
  - test_normalize_basic
  - test_normalize_unknown_preserved
  - test_normalize_empty_skills

- [x] T3: 既存テスト全PASS確認
  - ※8件の既存失敗は2A2実装前から存在（無関係）

- [ ] T4: dry-run実行してレポート確認（松野が実行・品質確認）
  - ユニークスキル数 before/after
  - 解決率
  - サンプル10名 before/after
