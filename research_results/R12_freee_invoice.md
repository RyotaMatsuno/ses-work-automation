# R12: freee請求書自動化 調査
調査日: 2026-06-18

## 結論（1行）
本番経路は `freee_invoice_v2.py` + `sheets_reader.py` で契約先別計算・源泉・支払サイト・GL月番号・/iv API は概ね正しいが、**FT階段粗利（75%/80%）未実装**・**`freee_invoice_monthly.py` が並行稼働（承認ゲートなし・60日バケット誤り・GL月番号なし）**・**Sheets読取の例外未捕捉**が残存リスク。

## 計算ロジック検証

**データフロー:** `sheets_reader.load_active_entries()` → 請求額 `seikyu` 計算 → `freee_invoice_v2.group_entries()` → `build_lines()` / `build_payload()` → POST `/iv/invoices`

**粗利:** `profit = tanka - shiire`（案件単価 − 仕入単価）。FT/GL は `profit <= 0` でスキップ。TERRA は粗利チェックなし。

| 契約先 | 粗利率 | 源泉徴収 | 支払サイト | 実装OK? |
|---|---|---|---|---|
| TERRA（BP通常） | 粗利×80% | 税抜×10.21%（行`withholding=True` + 見積`sub*1021/10000`） | Sheet「支払サイト」→30/45/60日バケット | ○ |
| TERRA（TERRA折半） | 粗利×50% | 同上 | 同上 | ○ |
| TERRA（岡本折半） | 粗利×80% | 同上 | 同上 | ○ |
| TERRA（プロパー・直契約） | 15,000円固定・合算行 | 同上 | 同上 | ○ |
| TERRA（GL/FT経由プロパー） | 請求なし | — | — | ○（`case`列 or 名寄せで除外） |
| FT（通常・岡本折半） | 粗利×68% | なし | **常に45日**（`get_payment_bucket` L91-92） | △（階段75%/80%未実装） |
| FT（小坂折半） | 粗利×48% | なし | 常に45日 | ○ |
| GL | 粗利×60% | なし | Sheet or 個人フォールバック（30/45日） | ○ |

**実装箇所（主要）**

| 項目 | ファイル | 行 |
|---|---|---|
| 請求額計算（TERRA/FT/GL） | `sheets_reader.py` | `_terra_entry` L179-219, `_ft_entry` L222-243, `_gl_entry` L246-263 |
| 源泉フラグ | `freee_invoice_v2.py` | `build_lines` L147, L162/176; `estimate_total_amount` L100-109 |
| 支払サイトバケット | `freee_invoice_v2.py` | `get_payment_bucket` L90-97, `payment_date` L121-125 |
| GL月番号 | `sheets_reader.py` | `_gl_entry` L262: `f"{name}様{m}月稼働分"` |
| GL/FT経由TERRAプロパー除外 | `sheets_reader.py` | `_terra_entry` L181-182; `load_active_entries` L349-354 |

**FT階段粗利（68%→75%→80%）:** 事業ルールに記載あるが、コード上は `_ft_entry` が **一律 0.68** のみ。件数カウントや契約マスター列からの切替ロジックは存在しない。

**並行スクリプト `freee_invoice_monthly.py`（`run_monthly_invoice.bat`）との差分**

| 項目 | v2 | monthly |
|---|---|---|
| データ取得 | `sheets_reader.load_active_entries`（稼働確定列・契約期間） | 独自 `load_people`（稼働中/月末終了のみ） |
| 件名 | `2026年7月分請求書` | `7月分請求書`（年なし） |
| 60日サイト | `return "60"` | `return "46"`（**バグ**: L102） |
| GL月番号 | あり | なし（`{name}様稼働分`） |
| `FREEE_WRITE_APPROVED` | 必須 | **なし** |
| `unit` | `""`（空欄） | `"式"` |

## freee API呼び出し

| 項目 | 仕様 | 実装 | OK? |
|---|---|---|---|
| 作成エンドポイント | POST `/iv/invoices` | `requests.post(f"{FREEE_BASE_INV}/invoices", ...)` L316 | ○ |
| 旧API廃止 | `/api/1/invoices` → 404 | 会計APIは取引先のみ（L202-217） | ○ |
| `company_id` | body トップレベル | `build_payload` L185 | ○ |
| `template_id` | 3323260 | L187 | ○ |
| `sending_status` | `unsent` | L196 | ○ |
| `unit_price` | 文字列型 | `str(person["seikyu"])` L173 | ○ |
| `unit` | 調査指示: 1文字以上（例: 式） | v2: `LINE_UNIT = ""` L50 | △（渋沢レビューは空欄を期待、`unit_check` L336-337） |
| 必須キー | `tax_fraction`, `withholding_tax_entry_method`, `partner_title` | L193-195（FIX済み） | ○ |
| 冪等性 | 重複防止 | `fetch_existing_invoice_keys` + `fetch_existing_invoice_triples` L401-411 | ○ |

**GET一覧も `/iv/invoices`:** 重複チェック・`shibusawa/invoice_review.py` の取得ともに `https://api.freee.co.jp/iv/invoices` を使用。

## 契約マスター（Google Sheets）取得

| 項目 | 内容 |
|---|---|
| SS ID | `1ORBtxtGqLAwv3YU8CGeLX7gWFgvKOivMTCZZiWtYGfI`（`sheets_reader.py` L27） |
| 認証 | `google_credentials.json` + gspread |
| シート | `TERRA` / `フラップテック` / `グレイスライン` |
| フィルタ | ステータス「稼働中」、契約期間内、`{年}年{月}月_稼働確定` 列（あれば TRUE 必須） |
| 列検索 | ヘッダー動的検索: 契約開始日・終了日・参画時期・期間・支払サイト |

## エラーハンドリング

| 障害 | 挙動 | 評価 |
|---|---|---|
| Sheets読取失敗 | `load_active_entries()` 内で未捕捉 → **プロセス全体クラッシュ** | △ |
| GET /iv/invoices 失敗（冪等） | `existing_keys`/`triples` が `None` → **全処理中止**（L402-410） | ○（安全側） |
| POST 失敗 | `NG` ログ出力、他グループは継続（L321-322） | ○ |
| 三重キー重複 | `DuplicateInvoiceError` → LINE通知松野（L426-430） | ○ |
| 支払サイト未入力（TERRA） | スキップ + LINE警告（`sheets_reader` L355-358） | ○ |

## 安全装置（確定防止）

| 装置 | 実装 | OK? |
|---|---|---|
| デフォルト dry-run | `dry_run = not args.execute`（v2 L465） | ○ |
| 実POST承認ゲート | `FREEE_WRITE_APPROVED=1` 必須（v2 L325-331, workflow L22-28） | ○（**monthly は未実装**） |
| 送信防止 | `sending_status: "unsent"`。POSTに `invoice_status` なし（draft相当） | ○ |
| 渋沢レビュー | `invoice_workflow.py` → `shibusawa/invoice_review.py`（draft-only、確定文言禁止 L75-81） | ○ |
| 手動確定後の送信 | `invoice_sender.py` は `confirmed/approved` のみ対象、デフォルト `--dry-run` | ○ |
| 二重請求防止 | partner×支払日 + partner×支払日×合計の二段チェック | ○ |

**注意:** `run_invoice.bat` は `freee_invoice_v2.py --execute` を直接呼ぶが、Python側で `FREEE_WRITE_APPROVED` 未設定時は `RuntimeError` で停止する。`run_monthly_invoice.bat` は **承認ゲートなし** で POST 可能。

## 推奨アクション

- [ ] **`freee_invoice_monthly.py` の退役または v2 への統合** — 承認ゲート・60日バケット・GL月番号・件名形式の不整合を解消
- [ ] **FT階段粗利（75%/80%）の実装方針確定** — 契約マスター列 or 稼働件数カウンタを SSoT に配線（現状は一律68%）
- [ ] **`load_active_entries()` 呼び出しに try/except を追加** — Sheets障害時にクラッシュせず松野LINE通知＋処理中止
- [ ] **`unit` 欄の方針統一** — freee API要件（1文字以上）と渋沢 `unit_check`（空欄期待）のどちらを正とするか決定
- [ ] **`run_monthly_invoice.bat` に `FREEE_WRITE_APPROVED=1` チェックを追加**、またはタスク登録を `invoice_workflow.py` 経由に一本化
- [ ] **TERRA BP の粗利≤0 チェック追加検討** — FT/GLのみ検証しており、異常データで請求0/マイナス行が出る余地あり
