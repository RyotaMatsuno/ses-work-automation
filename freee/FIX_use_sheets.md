# freee 請求 データ源をスプレッドシートに切替（Excel廃止）2026-06-08

## 対象ファイル
freee/freee_invoice_v2.py

## 背景・方針
契約マスターのデータ源は Google スプレッドシートのみ（ローカルExcelは廃止）。
スプレッドシート読込モジュール sheets_reader.py（ses_work 直下）が既にあり、
sheets_reader.load_active_entries() が同じ構造のエントリ
（partner/name/profit/seikyu/rule/source）を返す。これに切り替える。

## 実装内容（最小変更・2点のみ）

### (A) run() の中の対象人員取得を Excel版→Sheet版 に切り替える
現在の行:
    entries = load_active_entries()
を、次に置き換える:
    # 契約マスター = Googleスプレッドシートのみ（Excel廃止 2026-06-08）
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _root not in sys.path:
        sys.path.insert(0, _root)
    import sheets_reader
    entries = sheets_reader.load_active_entries()

### (B) 既存Excel版 load_active_entries() にDEPRECATEDコメントを付ける
- 関数 def load_active_entries(): の直前の行に、次のコメント1行を追加するだけ:
    # [DEPRECATED 2026-06-08] Excel読込。現在は sheets_reader.load_active_entries() を使用。
- 関数本体・EXCEL_PATH 定数は削除しない（参照が残る可能性があるため）。

## 厳守事項
- create_invoice / fetch_existing_subjects（冪等化）/ 金額ルール / auto_status は一切変更しない。
- 上記(A)(B)以外は変更しない。他ファイルも変更しない。
- os と sys は既に import 済みなので追加 import は不要。
- 完了後 python -m py_compile freee/freee_invoice_v2.py がクリーンであること。
