# CLAUDE.md — db_quality_fix 作業ルール

最終更新: 2026-06-10
設計: ジョブズ（GPT-4o壁打ち済み）

---

## このタスクの目的

Notionエンジニアビス取込パイプライン（mail_pipeline.py + matching_v3）が生成した
データ品質問題を2フェーズで解決する。

- **フェーズ1（本タスク）**: 既存DBの汚染レコードを検出・クレンジング
- **フェーズ2（後続）**: mail_pipelineの取込時バリデーション強化で再発防止

---

## 作業ディレクトリ

`ses_work/db_quality_fix/`

---

## 環境変数

`ses_work/config/.env` から読み込む。必須キー:
- `NOTION_API_KEY`
- エンジニアDB ID: `343450ff-37c0-819d-8769-fb0a8a4ceeb1`
- 案件DB ID: `343450ff-37c0-81e4-934e-f25f90284a3c`

---

## 絶対ルール（違反禁止）

1. **Notionレコードの物理削除は一切禁止** → `提案対象フラグ = False` に変更するのみ
2. **自動修正は dry_run=True がデフォルト** → `--live` フラグ明示時のみ実際に更新
3. **CostGuardを通すこと** → LLMは使用しない（本タスクはルールベースのみ）
4. **出力ファイルは `db_quality_fix/output/` に保存**
5. **エンコーディングは全てUTF-8**
6. **日本語パスをcwdに渡さない**（スクリプト内でパス解決すること）
7. **1回のNotionAPI呼び出しでpage_size=100、ページネーション対応必須**

---

## 禁止事項

- Notionレコードの hard delete（アーカイブも）
- `.env` の上書き・変更
- `matching_v3/` および `mail_pipeline.py` の変更（フェーズ2の範囲）
- LLMへの問い合わせ（本タスクはルールベースのみ）

---

## コーディング規約

```python
# ファイル冒頭必須
# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
```

- Notion APIは `requests` で直接呼ぶ（MCP経由不可）
- Notion APIバージョン: `2022-06-28`
- エラーは握りつぶさず `print(f"[ERROR] {e}")` で出力
- dry_run時は `[DRY-RUN]` プレフィックスで出力
