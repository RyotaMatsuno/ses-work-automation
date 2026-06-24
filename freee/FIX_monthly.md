# freee 請求書 月次自動発行ジェネレータ freee_invoice_monthly.py 仕様 2026-06-08

## 目的
毎月1日に「前月稼働分」の請求書(unsent下書き)を自動発行する汎用版。
freee/_proposal2.py と freee/freee_invoice_v3.py のロジックを一般化し、対象月を実行日から自動算出する。
※ _proposal2.py / freee_invoice_v3.py は変更しない。新規ファイル freee/freee_invoice_monthly.py のみ作成。

## 対象期間の自動算出（実行日=today, datetime.date.today()）
- 対象稼働月 = todayの前月（例: 7月実行→6月分、6月実行→5月分）
- 締め日 close = 前月末日
- billing_date = todayの月の1日（YYYY-MM-01）
- subject = f"{対象月の月}月分請求書"  （例 "6月分請求書"）
- payment_date(bucket) = close + bucket日数。土日は翌営業日。可能なら日本の祝日(7/20海の日,9/15敬老の日,9/22秋分,等)も翌営業日へ（jpholidayが無ければ土日のみでよい）

## バケット（_proposal2と同一）
- TR/GL: site(int)<=30→"30", 31-45→"45", >=46→"46"
- FT: 常に"45"

## 対象者 included(status)
- "稼働中" を含む → 含める
- f"{対象月の月}月末終了" を含む → 含める（前月末終了者は前月分を計上）
- それ以外（入場前・退場済み・他月末終了）→ 除外

## 金額（TERRAは「TERRA請求額」列= col15 を正本に）
TERRAタブ列: 担当0 区分1 status2 氏名3 単価7 サイト8 仕入13 粗利14 TERRA請求額15 案件6
- 区分P かつ 案件(col6)にGL/FT/グレイスライン/フラップテックを含む → スキップ（他社経由・請求なし）
- col15 を読む:
    - "請求なし"（その文字列を含む）→ スキップ
    - 数値（カンマ・円除去でintになる）→ その額で個別行 "氏名様稼働分"
    - 空欄:
        - 区分P → 15,000（プロパー定額）。プロパー集約行に入れる
        - 区分BP → 粗利(col7-col13)×率。TERRA折半=0.50 / 岡本折半=0.80 / それ以外BP=0.80。個別行
- 区分Pで col15=15000 or 空欄→15000 のものは「プロパー稼働分」1行に集約（quantity=人数、unit_price=15000）
- 集約に入らないTERRA明細（BP・col15個別数値）は "氏名様稼働分" 個別行
FTタブ列: 担当0 status1 氏名2 単価6 仕入7 サイト12
- 粗利(col6-col7)×（担当=="小坂折半"なら0.48 / それ以外0.68）。全員 "氏名様稼働分" 個別行
GLタブ列: status0 氏名1 単価5 仕入6 サイト10(空欄)
- 粗利(col5-col6)×0.60。サイトは {'石崎春光':'30','山内清':'45','荒井大輝':'45'} で補完、無ければスキップ＋警告。全員個別行

## グルーピング/POST（freee_invoice_v3.py と同一様式・実証済み）
- (partner, bucket) でグループ化
- partner_id: 株式会社TERRA=91256138 / 株式会社フラップテック=113795090 / グレイスライン株式会社=117422289
- payload: company_id=11712776, template_id=3323260, billing_date, payment_date(bucket),
  subject, payment_type="transfer", tax_entry_method="out", tax_fraction="omit",
  withholding_tax_entry_method="out", partner_title="御中", sending_status="unsent"
- 源泉: partner=="株式会社TERRA" の時のみ各line withholding=true、FT/GLはfalse
- line: {"type":"item","description","quantity","unit":"式","unit_price":str(...),"tax_rate":10,"reduced_tax_rate":False,"withholding":<bool>}
- 認証: from token_manager import get_headers（v2/v3と同じ、sys.pathにfreee_auth追加）。FREEE_BASE_INV="https://api.freee.co.jp/iv"
- 冪等化: GET /iv/invoices 全ページ取得し、billing_date==当月1日 かつ subject==対象月subject の既存の(partner_id,payment_date)集合を作りSKIP

## モード
- 既定 dry-run（payload表示・POSTなし）。コマンド引数 "--execute" の時のみ実POST。
- 先頭で「対象稼働月 / 締め日 / billing_date / subject」を表示。
- 各グループ OK(invoice_id)/SKIP/NG、末尾に 作成/SKIP/エラー件数。

## 厳守
- 既定dry-run（--execute無ければ絶対POSTしない）。
- py_compile通過。_proposal2.py / freee_invoice_v3.py は触らない。
