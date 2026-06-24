# TASKS.md - Phase3

- [x] 1. mail_pipeline.py の先頭importに `import hashlib` を追加（なければ）
- [x] 2. fetch_emails_from_account() 内のmsg_id生成を安定ハッシュに変更（SPEC変更1）
- [x] 3. main() 内のprojectメール処理からextract_affiliation/ai_matching/save_draft/send_proposal_emailを削除（SPEC変更2）
        - get_available_engineers()の呼び出しも削除
        - `affiliation = ""` 固定
        - `log(f"  [OK] 案件登録完了: {proj_name} → matching_v3が次回マッチング")` を追加
        - save_processed_id / continue は必ず残す
- [x] 4. send_batch() 内にledgerコスト記録を追加（SPEC変更3）
- [x] 5. syntax確認: `python -c "import py_compile; py_compile.compile('mail_pipeline/mail_pipeline.py', doraise=True); print('OK')"`
- [x] 6. pf3_mailpipeline/setup_schedules.py を作成して即実行（SPEC変更4）
        - SES_MailPipeline を60分毎に
        - SES_MatchingV3 を120分毎に
        - 各タスクのスケジュール変更結果をprint
