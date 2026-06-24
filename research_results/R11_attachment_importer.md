# R11: mail_attachment_importer 調査
調査日: 2026-06-18

## 結論（1行）
Phase 9 完了済みでパターン A/B/C のパイプラインは動作するが、型判定は拡張子のみ・`.xls`/`.doc` は実質非対応・`project_sheet_urls` は未配線・添付サイズ/パスワード保護の明示処理なしというギャップが残る。

## パターン別分析

### パターンA（添付ファイル）

**処理フロー**

```
mail_fetcher._fetch_new_emails_for_account()
  → Content-Disposition: attachment のパーツを走査
  → 拡張子が SUPPORTED_EXTS に一致するもののみ取得
importer.main() → process_attachments()
  → parsers.file_parser.parse_file() でテキスト化
  → 200文字未満は error カウントでスキップ
  → ai_extractor.classify_content() で engineer / project / unknown 判定
  → extract_engineers() または extract_projects()
  → utils.notion_writer.register_engineer() / register_project()
```

**対応形式**

| 拡張子 | パーサー | 実効性 |
|---|---|---|
| `.xlsx` | openpyxl (`data_only=True`, BytesIO 読み取り専用) | 良好 |
| `.xls` | openpyxl に委譲 | **要改善** — openpyxl は旧形式 `.xls` 非対応。例外 → `parse_file` が `None` 返却 |
| `.pdf` | pdfplumber | 良好（スキャンPDFはテキスト抽出不可の可能性） |
| `.docx` | python-docx | 良好 |
| `.doc` | python-docx に委譲 | **要改善** — 旧形式 `.doc` 非対応 |

**人員/案件の自動振り分け（Phase 8 追加）**

- `classify_content()` が LLM（`can_spend` 通過時）またはキーワードスコアリングで判定
- `engineer` → `extract_engineers` → エンジニア DB upsert（名前+所属）
- `project` → `extract_projects` → 案件 DB 登録（案件名重複チェック）
- `unknown` → skip カウント

**openpyxl creator metadata 上書き問題**

- 現行コードは `BytesIO` から **読み取りのみ**（`load_workbook(..., data_only=True)`）。保存処理は存在しない
- よって creator metadata の上書きリスクは **該当なし**（読み取り専用フロー）
- `data_only=True` は数式セルを計算結果として読むための設定であり、メタデータ対策ではない

### パターンB（単一URL）

**処理フロー**

```
mail_fetcher: 本文 _get_body_text() から SHEET_URL_PATTERN で URL 抽出
importer.main() → process_sheet_urls()
  → sheet_fetcher.fetch_sheet_text()（Playwright headless Chromium）
  → 50文字未満は error
  → extract_engineers()（1名分を想定）
  → register_engineer() × N
```

**パターン B と C のコード上の区別**

- **区別なし**。どちらも `process_sheet_urls()` → `extract_engineers()` の同一経路
- LLM が JSON 配列で返す人数に依存（1名なら B、複数名なら C）
- `test_mock_patterns.py` で B（1件）/ C（3件）をモック検証済み

**Spreadsheet URL 正規表現**

```python
SHEET_URL_PATTERN = re.compile(
    r'https://docs\.google\.com/spreadsheets/d/[A-Za-z0-9_\-]+[^\s\r\n"<>]*'
)
```

- `docs.google.com/spreadsheets/d/{ID}` 形式を本文から抽出
- `set()` で重複 URL を除去
- `/edit`, `/view`, `?gid=` 等のサフィックスも `[^\s\r\n"<>]*` で許容

**Playwright 取得**

- タイムアウト 15 秒、読み込み後 3 秒待機
- `accounts.google.com` / `ServiceLogin` リダイレクト → `login_required`（skip）
- 取得成功時テキスト上限 **50,000 文字**（`sheet_fetcher.py:47`）

### パターンC（複数人員リスト）

- パターン B と同一の `process_sheet_urls()` 経路
- `extract_engineers()` が複数要素の JSON 配列を返し、ループで `register_engineer()` を繰り返す
- スプレッドシート 1 URL に複数人がまとまっているケースを LLM 側で分解

**案件版 C（補足・未配線）**

- `importer.py` に `process_sheet_urls_projects()` と `project_sheet_urls` 分岐が存在
- しかし `mail_fetcher.py` は `project_sheet_urls` を **一切設定しない**
- スプレッドシート URL 経由の案件登録は現状 **到達不能（デッドコード）**
- 案件のスプレッドシート取込はパターン A（添付 + `classify_content` → project）でのみ可能

## 添付ファイルの型判定

| 方式 | 実装 | 評価 |
|---|---|---|
| 拡張子 | `Path(filename).suffix.lower()` と `SUPPORTED_EXTS` / `parse_file` の分岐 | **のみ使用** |
| MIME type | `part.get_content_type()` は参照せず | **未実装** |
| マジックバイト | なし | **未実装** |

**リスク**: `report.pdf` という名前の `.xlsx` ファイルは Excel パーサーで失敗し error になる。逆に拡張子偽装の検出もなし。

## CostGuard 適用（LLM 呼び出し箇所）

`common.ledger.can_spend()` / `record()` を `ai_extractor.py` で使用。

| 関数 | 推定トークン (in/out) | 上限到達時 | API 成功後 |
|---|---|---|---|
| `classify_content()` | 1000 / 50 | キーワード fallback（API キーなし時も同様） | `record()` |
| `extract_engineers()` | 2500 / 2000 | 空リスト `[]` 返却 | `record()` |
| `extract_projects()` | 2500 / 2000 | 空リスト `[]` 返却 | `record()` |

- グローバル上限: `COST_GUARD_DAILY_USD`（デフォルト $8）/ `COST_GUARD_MONTHLY_USD`（デフォルト $140）
- LLM 入力 truncate: classify 3000 文字、extract 8000 文字
- `reserve()` / フェーズ別 `DAILY_CALL_LIMIT` は **未使用**（`can_spend` のみ）
- `test_mock_patterns.test_costguard_blocks_llm` でブロック時スキップを検証済み

## エラーハンドリング

| 障害パターン | 処理 | 評価 |
|---|---|---|
| IMAP 接続失敗 | `ConnectionError` catch → スクリプト終了 | 良好 |
| ファイル破損 / 形式不一致 | `parse_file` が例外 catch → `None` → error カウント・継続 | 部分対応 |
| パスワード保護 Excel/PDF | 専用分岐なし。openpyxl/pdfplumber の汎用例外 → 同上 | **要改善** |
| 巨大ファイル | 添付サイズ上限なし（メモリに全読み込み）。LLM 入力は 8000 文字で truncate | **要改善**（メモリ） |
| テキスト短すぎ | 添付 200 文字未満 / シート 50 文字未満 → error | 良好 |
| スプレッドシート ログイン必要 | `login_required` → skip | 良好 |
| Playwright 未インストール | `status: error` → error | 良好 |
| Claude API / JSON 失敗 | 空リスト or unknown → error/skip | 部分対応 |
| Notion 登録失敗 | 最大 2 回リトライ（2 秒 sleep） | 良好 |
| 1 メール内の部分失敗 | 他の添付/URL は継続。UID は **常に処理済み記録** | **注意** — 失敗分の再処理不可 |

## パターン間の競合（添付 + URL 両方ある場合）

`importer.main()` のループ内で **独立に両方実行**（`SPEC.md` 記載どおり）:

1. `attachments` があれば `process_attachments()`（パターン A）
2. `sheet_urls` があれば `process_sheet_urls()`（パターン B/C）
3. `project_sheet_urls` があれば `process_sheet_urls_projects()`（未配線）

- 排他制御なし。同一メールから人員が二重登録される可能性あり（添付スキルシート + シート URL が同一人物の場合）
- 処理順: 添付 → 人員 URL → 案件 URL（後者は現状未到達）

## テスト結果

| コマンド | 結果 |
|---|---|
| `python -m pytest ses_work/mail_attachment_importer/tests/ -v` | **0 tests** — `tests/` ディレクトリ不存在 |
| `python test_mock_patterns.py`（実ディレクトリ直下） | **6/6 OK**（0.86s） |

**test_mock_patterns.py 内訳**

| テスト | 内容 | 結果 |
|---|---|---|
| `test_pattern_a_attachment` | 添付 → engineer 抽出 → Notion 登録 | pass |
| `test_pattern_b_single_sheet` | 単一 URL → 1 名登録 | pass |
| `test_pattern_c_multi_sheet` | 単一 URL → 3 名登録 | pass |
| `test_sheet_login_required_skipped` | ログイン必要シート skip | pass |
| `test_notion_upsert_by_name_and_affiliation` | 名前+所属検索 | pass |
| `test_costguard_blocks_llm` | CostGuard 上限時 LLM スキップ | pass |

**その他テストファイル**（調査指示の pytest 対象外）

- `test_integration.py` / `test_quick.py` — IMAP・Claude API 等の実接続が必要
- `test_imap.py` / `test_fetcher.py` — 手動確認用

## 推奨アクション

- [ ] `tests/` ディレクトリを作成し `test_mock_patterns.py` を pytest 収集可能に移行（または TASKS/調査手順のパスを修正）
- [ ] `.xls` は `xlrd` 等の別パーサー追加、`.doc` は変換または対象外明示で `SUPPORTED_EXTS` から除外
- [ ] `mail_fetcher.py` に `project_sheet_urls` 抽出ロジックを実装するか、`importer.py` のデッドコードを削除して仕様を統一
- [ ] 添付ファイルの MIME type / マジックバイト検証を追加し、拡張子不一致を早期検出
- [ ] 添付サイズ上限（例: 10MB）とパスワード保護ファイルの明示エラーメッセージを追加
- [ ] 1 メールに添付+URL 両方ある場合の重複登録防止（氏名ベース dedup または処理優先順位の定義）
- [ ] 部分失敗時の UID 処理済み記録ポリシーを見直し（全件成功時のみ mark_processed 等）
- [ ] `ai_extractor` に `reserve()` フェーズ制限を導入し、日次呼び出し回数を他モジュールと統一管理
