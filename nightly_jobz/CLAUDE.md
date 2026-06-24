# nightly_jobz Cursorルール

- 冒頭で `sys.stdout.reconfigure(encoding='utf-8', errors='replace')` を使用
- CostGuard必須: `cost_guard.allowed()` / `finalize()`
- Notion APIは REST 直叩き（MCPは使わない）
- Notion-Version: `2022-06-28`
- GPT呼び出しは OpenAI Responses API (`client.responses.create`)
- 日本語パス: `os.environ['USERPROFILE'] + OneDrive/デスクトップ/ses_work`
- DRY_RUNモードのテストを必ず作成
- メール送信・LINE送信は Phase 2 以降
