# freee /iv invoices 必須キー追加（実証済み・2026-06-08）

## 対象ファイル
freee/freee_invoice_v2.py の create_invoice 関数

## 背景
POST https://api.freee.co.jp/iv/invoices が 400 を返した:
not_exist_required_key:
"tax_fraction, withholding_tax_entry_method, partner_title が指定されていません。"

## 確定値（既存請求書 id=29049161 / partner=TERRA から GET で実証取得）
- tax_fraction = "omit"
- withholding_tax_entry_method = "out"
- partner_title = "御中"

## 変更内容
create_invoice 内の payload 辞書の【トップレベル】に、次の3キーをそのまま追加する。
（lines 配列の中ではない。payload 辞書の直下＝トップレベル。）

    "tax_fraction": "omit",
    "withholding_tax_entry_method": "out",
    "partner_title": "御中",

挿入位置の目安: payload 内の "tax_entry_method": "out", の直後でよい。

## 厳守事項（変更してはいけない）
- payload のトップレベルにのみ追加する
- 金額計算・unit_price・WITHHOLDING・dry_run 分岐・subject・lines の中身は一切変更しない
- 他の関数・他のファイルは変更しない
- 完了後 `python -m py_compile freee/freee_invoice_v2.py` がエラーなく通ること
