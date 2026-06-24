# freee 請求書 冪等化（二重請求防止）実装仕様 2026-06-08

## 対象ファイル
freee/freee_invoice_v2.py

## 目的
同じ「請求月×人物」の請求書が既にfreeeに存在する場合、再POSTせずスキップする。
全件実行の再実行・スケジューラ誤起動でも二重請求が起きないようにする。

## 実証済みの前提（このとおりに実装すること）
- 一覧API: GET https://api.freee.co.jp/iv/invoices
  - params: company_id=COMPANY_ID, limit=100, offset=N
  - レスポンスは {"invoices":[...]} 。meta は無い(null)。
  - billing_date 昇順で返り、最新分は末尾ページにある。
  - 全件取得は offset を 0,100,200... と増やし、取得件数 < 100 で停止。
- 各 invoice は "subject" と "billing_date" を持つ。
- 本スクリプトが作る subject の形式（人×月で一意）:
  f"{mon}分 業務委託料（{entry['name']}様）"
  ※ mon = f"{issue_date.year}年{issue_date.month}月"

## 実装内容（(1)(2)(3)のみ。それ以外は触らない）

### (1) 既存subject収集ヘルパーを新規追加（create_invoice の前あたりに置く）
def fetch_existing_subjects(issue_date):
    """対象請求月(billing_date==issue_date)の既存請求書 subject 集合を返す。取得失敗時は None。"""
    target = issue_date.strftime("%Y-%m-%d")
    subs = set()
    offset = 0
    while True:
        try:
            r = requests.get(f"{FREEE_BASE_INV}/invoices",
                             headers=freee_headers(),
                             params={"company_id": COMPANY_ID, "limit": 100, "offset": offset})
        except Exception as e:
            print(f"[dedup] 一覧取得エラー: {e}")
            return None
        if r.status_code != 200:
            print(f"[dedup] 一覧取得失敗 status={r.status_code}: {r.text[:150]}")
            return None
        invs = r.json().get("invoices") or []
        for inv in invs:
            if inv.get("billing_date") == target:
                s = inv.get("subject")
                if s:
                    subs.add(s)
        if len(invs) < 100:
            break
        offset += 100
    return subs

### (2) create_invoice を dedup 対応に変更
- シグネチャ変更:
  def create_invoice(entry, issue_date, due_date, dry_run=False, existing_subjects=None):
- 関数冒頭（payload より前）で mon と subject を変数化:
    mon = f"{issue_date.year}年{issue_date.month}月"
    subject = f"{mon}分 業務委託料（{entry['name']}様）"
- subject 算出の直後（partner 解決・payload 構築の前）に重複チェック:
    if existing_subjects and subject in existing_subjects:
        print(f"  SKIP {entry['name']} / {entry['partner']} / 既に{mon}分の請求書あり")
        return "skip"
- payload 内の "subject" は新設の subject 変数を使う:
    "subject": subject,
- payload の lines 内 description（f"業務委託料（{entry['name']}様）{mon}分"）はそのまま。
- dry_run 分岐・POST 処理・成功/失敗の戻り値(True/False)は従来どおり維持。

### (3) run() を dedup 対応に変更
- issue_date/due_date 算出後・対象人員ループの前に既存 subject を取得:
    existing = fetch_existing_subjects(issue_date)
    if existing is None:
        print("[dedup] 冪等チェックに失敗したため、二重請求防止のため処理を中止します。")
        return
    print(f"[dedup] {issue_date.strftime('%Y-%m-%d')} の既存請求書 {len(existing)} 件")
- カウンタに skipped を追加し、ループを変更:
    ok = ng = skipped = 0
    for e in entries:
        r = create_invoice(e, issue_date, due_date, dry_run=dry_run, existing_subjects=existing)
        if r == "skip":
            skipped += 1
        elif r:
            ok += 1
        else:
            ng += 1
- 完了表示に skipped を含める:
    DRY:  f"=== DRY-RUN完了: 作成予定{ok}件 / SKIP{skipped}件 / エラー{ng}件 ==="
    本番: f"=== 完了: 作成{ok}件 / SKIP{skipped}件 / エラー{ng}件 ==="

## 厳守事項
- 金額計算・unit_price・WITHHOLDING・税率・lines 内容・auto_status 連携は一切変更しない。
- 上記(1)(2)(3)以外は変更しない。他ファイルも変更しない。
- 完了後 python -m py_compile freee/freee_invoice_v2.py がクリーンであること。
