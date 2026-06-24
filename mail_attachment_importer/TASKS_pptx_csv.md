# TASKS.md - file_parser pptx/csv対応

- [ ] 1. pip install python-pptx --break-system-packages
- [ ] 2. file_parser.py: parse_pptx(data)関数を追加（全スライド＋テーブル、=== スライド N ===区切り）
- [ ] 3. file_parser.py: parse_csv(data)関数を追加（UTF-8→cp932フォールバック、タブ区切りテキスト化）
- [ ] 4. file_parser.py: parse_file()の分岐に .pptx/.ppt → parse_pptx と .csv/.tsv → parse_csv を追加
- [ ] 5. python -c "from pptx import Presentation; print('pptx OK')"
- [ ] 6. python -m py_compile file_parser.py
- [ ] 7. python -c "import sys; sys.path.insert(0,'.'); from file_parser import parse_file; print('parse_file OK')"
