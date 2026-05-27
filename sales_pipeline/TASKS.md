# TASKS.md - Phase1 営業パイプライン 実装チェックリスト

最終更新: 2026-05-25

---

## 実装順序（この順番で実装すること）

- [x] T01: `sales_pipeline/` ディレクトリ作成・`drafts/` と `logs/` サブディレクトリ作成
- [x] T02: `templates.py` 実装 — 意向確認メールテンプレート・提案文テンプレート定義
- [x] T03: `step1_generate.py` 実装 — result.jsonを読み、意向確認メール文を生成してdrafts/に保存
- [x] T04: `step2_send.py` 実装 — drafts/の意向確認メールをmail_server.py HTTP経由で送信（dry_run対応）
- [x] T05: `step3_parse.py` 実装 — ses-mailサーバーから未読メールを取得し、返信内容を解析してJSONに保存
- [x] T06: `step4_judge.py` 実装 — 並行スコア計算・必須スキル判定・粗利チェック・提案可否判定
- [x] T07: `step5_proposal.py` 実装 — 提案文生成（Claude API使用）・drafts/に保存
- [x] T08: `step6_send_proposal.py` 実装 — 提案文をmail_server.py HTTP経由で送信（dry_run対応）
- [x] T09: `pipeline.py` 実装 — Step1〜6を順番に呼び出すCLIエントリーポイント（--dry-runフラグ対応）
- [x] T10: smoke test実行 — `python sales_pipeline/pipeline.py --dry-run` が正常終了することを確認

---

## 完了基準

- T10のsmoke testが `returncode=0` で完了すること
- drafts/に意向確認メールサンプルが1件以上生成されること
- dry-run時にメール送信が実行されないこと
- ログがlogs/send_log.jsonに書き出されること

---

## 注意事項

- `config/.env` のパス: `C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env`
- ses-mailサーバーのポートは `.env` の `SESMAIL_PORT` から取得（デフォルト8766）
- result.jsonが存在しない・空の場合は空リストとして扱いエラーにしない
- 各stepは単体でも動作するようにすること（`python step1_generate.py` で実行可能）
- TASKS.md の各タスク完了後に `- [ ]` を `- [x]` に更新すること
