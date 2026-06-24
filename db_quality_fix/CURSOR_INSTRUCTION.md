【Cursor作業指示】v1.0
作成: ジョブズ 2026-06-10
優先度: 🔴 最高（外国籍人材の誤提案リスクが現在進行中）

---

## 対象ディレクトリ
`ses_work/db_quality_fix/`

## 参照ファイル（必読）
1. `ses_work/db_quality_fix/CLAUDE.md` — 作業ルール・禁止事項
2. `ses_work/db_quality_fix/SPEC.md` — 仕様書（検出パターンP1〜P7）
3. `ses_work/db_quality_fix/TASKS.md` — 実装チェックリスト
4. `ses_work/CLAUDE.md` — プロジェクト全体ルール
5. `ses_work/config/.env` — 環境変数（読み込みのみ）

## 作業内容
`ses_work/db_quality_fix/cleaner.py` を新規作成せよ。

## 完了条件
以下が全て満たされること:

1. `python cleaner.py`（dry_runモード）でエラーなく完了する
2. エンジニアDB全件を取得し、P1〜P7を検出してコンソールに出力する
3. `output/report_YYYYMMDD_HHMMSS.txt` と `.json` が生成される
4. `python cleaner.py --live` で実際にNotionが更新される
5. `time.sleep(0.35)` によるAPI呼び出し制限が実装されている
6. dry_runモードでは Notion の書き込みが一切発生しない

## 制約（CLAUDE.mdより抜粋・重要なものを再掲）
- Notionレコードの物理削除・アーカイブ禁止
- 提案対象フラグをFalseにするのみ
- LLM未使用（ルールベースのみ）
- UTF-8エンコーディング必須
- Notion APIバージョン: `2022-06-28`

## 実装上の注意
- Notion DB queryエンドポイント: `POST https://api.notion.com/v1/databases/{id}/query`
- Notion page updateエンドポイント: `PATCH https://api.notion.com/v1/pages/{id}`
- ページネーション: レスポンスの `has_more` が True の間、`start_cursor` を使って継続取得
- `除外理由` プロパティは `rich_text` 型。既存テキストを保持して先頭に付記
- `備考（LINEメモ）` プロパティ名に括弧が含まれることに注意（URLエンコード不要、JSONで指定）

## 質問がある場合
`ses_work/db_quality_fix/` 内に `QUESTION.md` を作成してジョブズに確認を求めること。
コードを勝手に変更せず、必ず確認を取ること。

---
以上
