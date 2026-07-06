# Phase 2A2: スキル正規化パイプライン — CLAUDE.md

## 絶対ルール
1. LLM呼び出しなし（辞書ベースのみ）
2. 既存「スキル」フィールドは上書きしない
3. 「正規化スキル」フィールドのみ書き込み
4. 未解決スキルはrawテキストをそのまま保持
5. build_skill_indexは変更しない（既に正規化スキル優先の実装済み）

## コーディング規約
- sys.stdout.reconfigure(encoding='utf-8', errors='replace')
- 型ヒント使用
- テスト: cd matching_v3 && python -m pytest tests/ -v
