# 【Cursor作業指示】Task N: Pipeline DB Work Queue統合 + Reclassification

対象ディレクトリ: ses_work/mail_pipeline/
作業内容: IMAP-only処理からDB work queue統合へアーキテクチャ修正
参照ファイル: CLAUDE.md / mail_pipeline/SPEC.md
完了条件: DB上のprocessed=0レコードが自動消化される + テスト通過
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 背景・問題

現在の`_main_body()`はIMAPから取得したメールのみを処理対象にしている。
DB上で`processed=0`にリセットされたレコード（再分類対象）を再処理するパスが存在しない。

（以下仕様省略 — 元ファイルと同一）

---

## 完了メモ（2026-06-19）

- `raw_inbox.py`: `fetch_unprocessed_from_db()` 追加（NULL優先→other順、`_source=db_backlog`）
- `mail_pipeline.py`: `_reclassify_by_rule()` 追加、`_main_body()` を DB work queue ベースに変更
- `finalize_processed_state()`: `processed=None` 対応（in-memory set 不要）
- メトリクス: `mails_fresh`, `mails_reclass`, `reclass_attempted`, `reclass_promoted`, `db_backlog_remaining`
- LINE通知: `新規:N(fresh:X+reclass:Y) / 昇格:Z件 残backlog:W件` 形式
- `config/.env`: `DAILY_CALL_LIMIT_DEFAULT=50`（再分類extract余裕）
- pytest 78件中 74 passed（Task N 新規6件含む）
