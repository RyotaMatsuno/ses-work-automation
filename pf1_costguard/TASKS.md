# TASKS.md - Phase1

- [ ] 1. `../cost_guard.py` を全面書き直し（SPEC.md仕様通り）
        - 定数・STATE_FILE・ACTIVE_TASKS・get_costs()・disable_tasks()・enable_tasks()・main()を実装
        - 既存ファイルを完全上書き（バックアップ不要）
        - 文字コード UTF-8
        - 日本語コメント可
- [ ] 2. `setup_schedule.py` を作成し即実行
        - SES_CostGuardのスケジュールを5分毎に変更
        - 変更後にすぐ1回実行（schtasks /Run）
        - 結果をprint
- [ ] 3. syntax確認: `python -c "import py_compile; py_compile.compile('../cost_guard.py', doraise=True); print('OK')"` を実行して確認
