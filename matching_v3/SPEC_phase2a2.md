# Phase 2A2: スキル正規化パイプライン — SPEC.md
Version: 1.0
Date: 2026-06-26

## 目的
エンジニアDBの「正規化スキル」フィールド（現在0%）を投入し、
skill_indexの精度を向上させる。

## 方針（GPT-5.4合意済み）
- alias/synonymsのみ正規化。hierarchy統合はしない
- rawスキルへのフォールバックを維持（正規化スキルが空なら生スキルを使用）
- 投入前にサンプルレビューで品質確認

## 変更内容

### 1. スキル正規化バッチスクリプト (scripts/normalize_all_skills.py)
全エンジニアの「スキル」をskill_aliases.jsonで正規化 → 「正規化スキル」に書き込み

フロー:
1. get_all_engineers() で全208件取得
2. 各エンジニアの「スキル」をnormalizer.resolve_canonical()で解決
3. 解決できたスキルのみを「正規化スキル」に書き込み
4. 解決できなかったスキルもそのまま保持（rawとして追加）

dry-run: 結果をJSONレポートに出力
apply: Notion更新（update_engineer_normalized_skills使用）

### 2. build_skill_index の挙動確認
既存: `engineer.get("正規化スキル") or engineer.get("スキル")`
→ 正規化スキルが投入されれば自動的にそちらを使用。変更不要。

### 3. 正規化品質レポート
- 正規化前/後のユニークスキル数
- 解決率（canonical / total）
- 未解決スキル一覧
- サンプル10名の before/after

## テスト要件
1. 既存テスト全PASS
2. 新テスト:
   - test_normalize_basic: Java → Java, React.js → React
   - test_normalize_unknown_preserved: 未知スキルがそのまま保持される
   - test_normalize_empty_skills: スキルなしエンジニアはスキップ
3. dry-runレポート確認

## 制約
- LLM呼び出しなし（辞書ベースのみ）
- 既存スキル（生データ）は上書きしない
- 正規化スキルのみ書き込み
