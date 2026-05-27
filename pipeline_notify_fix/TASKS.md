# TASKS.md - pipeline_notify_fix

- [x] 1. mail_pipeline.py: change FETCH_LIMIT=500, PROCESS_LIMIT=500
- [x] 2. mail_pipeline.py: update fetch_recent_emails() to use SINCE today + fallback to ALL
- [x] 3. matching_v2.py: add raw_body to project dict in fetch/query logic
- [x] 4. matching_v2.py: add raw_body to engineer dict (from Notion field)
- [x] 5. matching_v2.py: include raw_body in result.json output per item and per candidate
- [x] 6. notify_line.py: add raw_body to get_page_info() project block
- [x] 7. notify_line.py: add raw_body to get_page_info() engineer block
- [x] 8. notify_line.py: add raw_body to empty_page_info() for both types
- [x] 9. notify_line.py: main() fills project_info raw_body from result.json fallback
- [x] 10. notify_line.py: main() fills engineer_info raw_body from candidate fallback
- [x] 11. notify_line.py: build_project_message() appends project raw_body section
- [x] 12. notify_line.py: build_project_message() appends per-engineer raw_body section
- [x] 13. py_compile mail_pipeline/mail_pipeline.py -> no error
- [x] 14. py_compile matching_v2/matching_v2.py -> no error
- [x] 15. py_compile matching_v2/notify_line.py -> no error
- [x] 16. python matching_v2/notify_line.py --dry-run -> exits 0 with raw_body shown
