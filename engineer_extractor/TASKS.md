# TASKS.md - Engineer DB Quality Improvement Pipeline

## Phase 1A: Parser Foundation
- [x] A1. engineer_text_parser.py 作成
  - Pattern 1/2/3 判定ロジック
  - subject / body / labeled_fields 分離
  - ParsedEngineerText dataclass
- [x] A2. tests/test_parser.py 作成
  - 各パターンのテストケース（サンプルテキスト）
  - エッジケース（空テキスト、混合パターン）

## Phase 1B: High-Impact Extractors
- [x] B1. skill_dictionary.json 作成（200+語）
- [x] B2. field_extractors/skills_extractor.py 作成
  - Layer 1: labeled extraction
  - Layer 2: subject bracket extraction  
  - Layer 3: dictionary matching
  - Layer 4: tech-token heuristic (optional)
- [x] B3. field_extractors/rate_extractor_eng.py 作成
  - 件名パターン（【7月〜65万】等）
  - ラベルパターン（【単価】40万円等）
  - レンジ/MAX/応相談対応
- [x] B4. field_extractors/station_extractor.py 作成
  - ラベル/body/subject優先順位
  - 路線名・エリア抽出
- [x] B5. tests/test_extractors.py 作成
  - 各extractor × 各パターンのテストケース

## Phase 1C: Secondary Extractors
- [x] C1. field_extractors/experience_extractor.py 作成
- [x] C2. field_extractors/availability_extractor.py 作成
  - 年補完ロジック（受信日基準）
- [x] C3. field_extractors/demographics_extractor.py 作成
- [x] C4. tests にテスト追加

## Phase 1D: Merge & Execution
- [x] D1. merge_policy.py 作成
  - empty判定ロジック
  - conflict detection
  - update candidate生成
- [x] D2. update_runner.py 作成
  - --dry-run / --shadow-write / --apply モード
  - Notion全件fetch
  - 各extractor実行
  - merge policy適用
  - レポート生成
- [x] D3. rollback_runner.py 作成
  - pre_update_snapshot保存
  - 差し戻しロジック

## Phase 1E: Dry-Run & Verification
- [x] E1. 全208件でdry-run実行
- [x] E2. summary report確認
- [x] E3. 30件サンプルmanual review
- [x] E4. 精度確認・抽出器修正

## Phase 1F: Production Apply
- [x] F1. 10件限定apply
- [x] F2. 結果確認
- [x] F3. 50件apply
- [x] F4. 全件apply（残135件 — 稼働可能日115件含む）
- [x] F5. After metrics計測
