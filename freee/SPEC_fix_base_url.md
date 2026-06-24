# SPEC: freee請求書APIベースURL修正

## 問題
`freee_invoice_v2.py` の `FREEE_BASE = "https://api.freee.co.jp/api/1"` が間違い。
POST /api/1/invoices は 404 を返す。

## 修正内容
`freee/freee_invoice_v2.py` の1箇所だけ変更する。

### 変更前
```python
FREEE_BASE = "https://api.freee.co.jp/api/1"
```

### 変更後
```python
FREEE_BASE = "https://api.freee.co.jp/invoice/v1"
```

## 確認済み事項
- GET `https://api.freee.co.jp/invoice/v1/invoices` → 200 OK（疎通確認済み）
- GET `https://api.freee.co.jp/invoice/api/1/invoices` → 200 OK（こちらも使用可）
- `partners` APIは `https://api.freee.co.jp/api/1/partners` → 200（こちらは会計APIなので変えない）

## 重要
`FREEE_BASE`は請求書作成（`/invoices` POST）にのみ使う。
`get_or_create_partner` 関数内の取引先APIは別URLのため変えてはいけない。

具体的には：
- `get_or_create_partner` の `f"{FREEE_BASE}/partners"` → このFREEE_BASEだけ会計API(`api/1`)のまま残す必要がある
- `create_invoice` の `f"{FREEE_BASE}/invoices"` → invoice/v1に変更が必要

## 修正方針（シンプルに）
定数を2つに分ける:

```python
FREEE_BASE_ACCT = "https://api.freee.co.jp/api/1"      # 会計API（取引先など）
FREEE_BASE_INV  = "https://api.freee.co.jp/invoice/v1"  # 請求書API
```

`get_or_create_partner` は `FREEE_BASE_ACCT` を使う。
`create_invoice` は `FREEE_BASE_INV` を使う。

## テスト
修正後に `python -c "import py_compile; py_compile.compile('freee_invoice_v2.py')"` でシンタックスエラーなし確認。
