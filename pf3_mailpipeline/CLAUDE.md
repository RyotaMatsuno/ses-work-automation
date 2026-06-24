# CLAUDE.md - Phase3: mail_pipeline 再構築

## 目的
mail_pipelineの「30分毎にai_matching(max_tokens=2000)を全projectメールに実行」という
コスト爆発の根本原因を除去し、「分類+Notion登録専用」に絞り込む。
マッチングはmatching_v3に一本化する。

## 変更対象ファイル
1. `mail_pipeline/mail_pipeline.py` - メイン修正（スキップ量：多いが精度必須）
2. スケジューラ設定スクリプト（新規作成・実行）

## 絶対禁止
- IMAP接続・Notion書き込み・LINE通知ロジックを壊してはいけない
- register_project() / register_engineer() の内部は変更しない
- processed_ids の読み書きロジックは変更しない（save_processed_id/load_processed_ids関数はそのまま）
- バックアップ(*.bak_*)ファイルは触らない
- mail_pipeline.py以外のsys pathのpyファイルは修正しない
