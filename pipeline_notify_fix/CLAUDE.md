# CLAUDE.md - pipeline_notify_fix

## Target files
- ses_work/mail_pipeline/mail_pipeline.py
- ses_work/matching_v2/matching_v2.py
- ses_work/matching_v2/notify_line.py

## Rules
- UTF-8 encoding required
- Do NOT send actual LINE messages (use --dry-run only for testing)
- Do NOT hardcode API keys (read from config/.env)
- Do NOT modify .bak_* files
