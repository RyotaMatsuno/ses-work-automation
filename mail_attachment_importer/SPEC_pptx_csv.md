# SPEC.md - file_parser.py pptx/csv対応追加

## 修正対象
`ses_work/mail_attachment_importer/file_parser.py` のみ

## 追加内容

### 1. parse_pptx(data: bytes) -> str
- python-pptxを使用（`from pptx import Presentation`）
- 全スライドのtextframeテキストを抽出
- テーブル内セルのテキストも抽出
- スライド番号を `=== スライド N ===` で区切る

### 2. parse_csv(data: bytes) -> str
- 標準ライブラリのcsvモジュールを使用（外部依存なし）
- エンコード: UTF-8 → 失敗したらcp932（Shift-JIS）でフォールバック
- 全行をタブ区切りでテキスト化

### 3. parse_file()の拡張子マッピングに追加
- `.pptx` / `.ppt` → parse_pptx()
- `.csv` / `.tsv` → parse_csv()

## インストール
- `pip install python-pptx --break-system-packages`
- csvは標準ライブラリのため追加不要

## 変更しないもの
- parse_excel / parse_pdf / parse_word は一切触らない
- 他ファイルは変更しない

## 確認コマンド
- `python -c "from pptx import Presentation; print('pptx OK')"`
- `python -m py_compile file_parser.py`
- `python -c "import sys; sys.path.insert(0,'.'); from file_parser import parse_file; print('parse_file OK')"`
