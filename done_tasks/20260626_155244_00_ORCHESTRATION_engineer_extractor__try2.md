# 00_ORCHESTRATION_engineer_extractor.md
# Phase 1: Engineer DB Quality Improvement Pipeline
# Created: 20260626_155244

## Overview
エンジニアDB（208件）の備考LINEメモ・原文からスキル/単価/最寄り駅等を自動抽出し、
空欄フィールドを補完するルールベースパイプライン。

## Execution Order
すべてのタスクは engineer_extractor/ ディレクトリ内で実行する。
SPEC.md, CLAUDE.md, TASKS.md は同ディレクトリに配置済み。

### Task 1: Parser + Dictionary (並列不可 - 基盤)
File: 01_parser_and_dictionary.md
- engineer_text_parser.py 作成
- skill_dictionary.json 作成（200+語）
- tests/test_parser.py 作成

### Task 2: Field Extractors (Task 1完了後)
File: 02_field_extractors.md
- field_extractors/skills_extractor.py
- field_extractors/rate_extractor_eng.py
- field_extractors/station_extractor.py
- field_extractors/experience_extractor.py
- field_extractors/availability_extractor.py
- field_extractors/demographics_extractor.py
- tests/test_extractors.py

### Task 3: Merge & Runner (Task 2完了後)
File: 03_merge_and_runner.md
- merge_policy.py
- update_runner.py (--dry-run / --shadow-write / --apply)
- rollback_runner.py
- tests/test_merge.py

## Dependencies
- Task 1 → Task 2 → Task 3 (sequential)
- config/.env の NOTION_API_KEY を使用
- Notion DB ID: 343450ff-37c0-819d-8769-fb0a8a4ceeb1

## Completion Criteria
- 全テストパス
- dry-run実行でレポート生成成功
- apply実行不要（dry-run確認後にジョブズが判断）


## RETRY 1 REASON
target_file not found: 
