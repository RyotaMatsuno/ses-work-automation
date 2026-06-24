# GPT Wall-Hit: LINE Engineer Registration Failure
Date: 2026-06-22

## Root Cause
line_bridge.py classify_route()にURL検知がなく、Google Sheets付きメッセージが
developmentキーワードに引っかかり「自動処理対象外」として弾かれた。
webhook_server.pyのhandle_sheet_url()に到達しない。

## GPT Recommended Architecture (AGREED)
1. line_bridge.py classify_route()の最上部でURL/候補者フォーマット先行検知
2. 新ルート「candidate_intake」→ development判定より優先
3. 本文解析メイン、スプレッドシート解析はfallback
4. 確認付き半自動（Phase 1）→ 精度安定後に自動化
5. 重複防止（message_id冪等性 + Notion natural key重複チェック）
