"""後方互換: parsers.file_parser へのリエクスポート"""

from parsers.file_parser import parse_excel, parse_file, parse_pdf, parse_word

__all__ = ["parse_excel", "parse_file", "parse_pdf", "parse_word"]
