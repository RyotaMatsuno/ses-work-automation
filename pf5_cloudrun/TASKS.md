# TASKS.md - Phase5

- [x] 1. webhook_server.py の call_claude() 先頭に LLM_KILLチェック追加（変更1）
- [x] 2. webhook_server.py の analyze_skill_sheet() 内 requests.post 直前に LLM_KILLチェック追加（変更2）
         - 既存の戻り値型を確認して型を合わせること（{} or None）
- [x] 3. skill_extractor.py のLLM呼び出し箇所を特定してLLM_KILLチェック追加（変更3）
         - 戻り値型に合わせること
- [x] 4. syntax確認: `python -c "import py_compile; py_compile.compile('line_webhook/webhook_server.py', doraise=True); py_compile.compile('line_webhook/skill_extractor.py', doraise=True); print('ALL OK')"`
- [x] 5. TASKS.md のチェックボックスを全て[x]に更新
