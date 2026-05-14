# TASKS.md - メールパイプライン自動化

最終更新: 2026-05-08

- [x] CLAUDE.md 作成
- [x] SPEC.md 作成
- [x] TASKS.md 作成
- [x] Task 1: mail_pipeline.py 実装（v2: Message-IDによる重複防止・全メール対象）
- [x] Task 2: run_pipeline.bat 作成
- [x] Task 3: Windowsタスクスケジューラ登録（30分おき）
- [ ] Task 4: 動作テスト（jobz-commandサーバー復活後にジョブズが自動実行）
- [ ] Task 5: タスクスケジューラ自動実行確認

## 変更履歴
- v1: 未読フィルターで重複防止
- v2: Message-IDで重複防止（未読既読問わず全件処理）、processed_ids.json管理
