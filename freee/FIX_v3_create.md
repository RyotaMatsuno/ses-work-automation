# 5月分 請求書 本発行ジェネレータ freee_invoice_v3.py 仕様 2026-06-08

## 目的
freee/_proposal2.py の計算ロジックをそのまま使い、各「取引先×バケット」グループを
freee /iv API で請求書(unsent下書き)として作成する production スクリプト
freee/freee_invoice_v3.py を新規作成する。

## ベース（計算は _proposal2.py を一切変えずに流用）
freee/_proposal2.py の以下をそのまま使う:
- Sheet読込（TERRA/フラップテック/グレイスライン）
- included()（稼働中 or 5月末終了）
- bucket()（TR/GL: <=30→"30", 31-45→"45", >=46→"46" / FT→"45"固定）
- 金額計算（プロパー15000・齋藤11/18・BP/FT/GL各率）
- 除外（GL/FT経由のP・サイト/単価空白）
- groups（(partner,bucket)でグルーピング、プロパー集約）
- pay_date(bucket)（2026-05-31 + bucket日数、土日は翌営業日）

## POSTペイロード（freee/freee_invoice_v2.py の create_invoice を踏襲＝実証済み）
- 認証: `from token_manager import get_headers`（v2と同じ。sys.pathにfreee_authを追加）
- FREEE_BASE_INV="https://api.freee.co.jp/iv" / COMPANY_ID=11712776 / TEMPLATE_ID=3323260
- partner_id 辞書:
    '株式会社TERRA'→91256138 / '株式会社フラップテック'→113795090 / 'グレイスライン株式会社'→117422289
- 各グループ (partner, bucket) の payload:
    company_id, partner_id(辞書), template_id,
    billing_date="2026-06-01", payment_date=pay_date(bucket),
    subject="5月分請求書",
    payment_type="transfer", tax_entry_method="out", tax_fraction="omit",
    withholding_tax_entry_method="out", partner_title="御中", sending_status="unsent",
    lines=[...]
- withholding_flag = (partner == '株式会社TERRA')   # TERRAのみ源泉あり
- lines:
    - プロパー集約があれば1行:
        {"type":"item","description":"プロパー稼働分","quantity": round(pm,2),
         "unit":"式","unit_price":"15000","tax_rate":10,"reduced_tax_rate":False,"withholding": withholding_flag}
    - 個別 各人:
        {"type":"item","description": f"{name}様稼働分","quantity":1,
         "unit":"式","unit_price": str(amount),"tax_rate":10,"reduced_tax_rate":False,"withholding": withholding_flag}

## 冪等化
作成前に GET /iv/invoices を全ページ取得（limit=100,offset=0,100..., 取得<100で停止）。
billing_date=="2026-06-01" かつ subject=="5月分請求書" の既存請求書の (partner_id, payment_date) 集合を作る。
作成対象グループの (partner_id, payment_date) が既存にあれば「SKIP（既存あり）」しPOSTしない。

## 実行モード
- 既定は dry-run（payload表示・POSTなし）。
- コマンド引数に "--execute" がある時のみ実POST。
- 出力: 各グループ OK(invoice_id) / SKIP / NG、最後に 作成/SKIP/エラー件数と合計。

## 厳守
- _proposal2.py の計算（金額・按分・バケット・除外・源泉判定・対象者・支払期限）は一切変えない。
- 既定 dry-run（--executeが無ければ絶対にPOSTしない）。
- py_compile が通ること。他ファイルは変更しない。
