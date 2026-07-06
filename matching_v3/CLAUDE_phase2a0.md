# Phase 2A0: Retrieval Collapse Fix — CLAUDE.md

## 絶対ルール
1. 変更対象は matching_v3/matcher.py の filter_engineers_by_required_skills のみ
2. judge_with_meta は一切変更しない
3. apply_hard_filters は一切変更しない
4. matching_v3.py のメインフローは変更しない
5. 既存テストを壊さない
6. LLM呼び出しを追加しない（ルールベースのみ）

## コーディング規約
- sys.stdout.reconfigure(encoding='utf-8', errors='replace') をスクリプト冒頭に
- 型ヒント使用（from __future__ import annotations）
- logger使用（既存のlogger変数を流用）
- 日本語コメント可

## テスト実行
cd matching_v3 && python -m pytest tests/ -v

## 変更の意図
AND集合演算（全スキル一致必須）→ 閾値ベース（50%以上のスキル一致で候補に含める）
これにより候補生成段階で0名になる問題を解消。
スコアリング（judge_with_meta）が候補のランク付けを担当するため、
候補が増えても品質はスコアリング段階で担保される。
