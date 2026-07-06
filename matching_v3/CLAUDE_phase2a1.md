# Phase 2A1: ステータス管理 + Active Pool — CLAUDE.md

## 絶対ルール
1. LLM呼び出しなし（キーワードマッチのみ）
2. 147名の未設定エンジニアは空欄のまま（"稼働可能"にデフォルトしない）
3. 除外ロジックのみ: 稼働状況="稼働中"のみ除外
4. 提案対象フラグ・staleness_checker は変更しない
5. matching_v3.pyのメインフローは変更しない

## Active Pool定義
提案対象フラグ=True AND staleness OK AND 稼働状況 != "稼働中"
※空欄・稼働可能・調整中はすべてActive Pool対象

## コーディング規約
- sys.stdout.reconfigure(encoding='utf-8', errors='replace')
- 型ヒント使用
- テスト: cd matching_v3 && python -m pytest tests/ -v
