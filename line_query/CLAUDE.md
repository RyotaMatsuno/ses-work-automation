# CLAUDE.md - line_query

## Role
LINE official account query text parser.
Cross-searches Notion engineer/project DBs and returns full match results as LINE reply strings.

## Location
ses_work/line_query/line_query.py

## Caller
Import from ses_work/line_webhook/webhook_server.py handle_message()

## Rules
- Do NOT modify webhook_server.py existing logic (only add 3 lines at top of handle_message)
- Do NOT include LINE send logic here (return reply text string only)
- Do NOT use Notion MCP. Use requests library to call REST API directly
- Always load env vars from config/.env using dotenv_values
- No hardcoding (DB IDs, tokens, thresholds must be constants or .env)

## Dependencies
- requests
- python-dotenv (dotenv_values)
- jpholiday
- python-dateutil

## Test Method
python line_query.py
(Run 4 mock test cases in __main__ block)
