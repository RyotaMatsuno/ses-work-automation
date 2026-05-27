# SPEC: attachment_importer v1
# 人員情報（テキスト+添付ファイル）の自動取り込み・Notion登録・スキル判定

最終更新: 2026-05-26

---

## 概要

LINE/メールで届く人員情報（テキストサマリー + スキルシートファイル）を自動で解析し、
エンジニアDBにNotionへ登録する。
登録後、matching_v2が次回実行時にスキルシート情報を含めて○×判定を行う。

---

## ディレクトリ構成

```
ses_work/attachment_importer/
  CLAUDE.md         ← Codex作業ルール
  SPEC.md           ← 本ファイル
  TASKS.md          ← 実装チェックリスト
  importer.py       ← メインスクリプト
  parsers/
    text_parser.py  ← テキストサマリー解析（Claude API使用）
    file_parser.py  ← ファイル解析（Excel/Word/PDF/Gスプレッドシート）
    skill_matcher.py← スキル○×判定（Claude API使用）
  utils/
    notion_writer.py← Notion登録処理
    drive_downloader.py ← GoogleスプレッドシートをExcelとしてDL
  tests/
    test_text_parser.py
    test_file_parser.py
```

---

## 入力ルート

### ルートA: LINEから（webhook経由）
- webhook_server.pyがLINEメッセージを受信
- テキストメッセージ受信 → pending_textに一時保存（送信者ID + タイムスタンプ付き）
- ファイルメッセージ受信（Excel/Word/PDF）→ ローカルに保存
- テキスト受信から30分以内にファイルが来た場合 → importer.pyを起動
- 30分経過してもファイルが来なければ → pendingを破棄（ファイルなしは処理しない）

### ルートB: メールから（mail_pipeline.py経由）
- mail_pipeline.pyが添付ファイルを検出した場合 → importer.pyを呼び出す
- テキスト本文 + 添付ファイルパスをimporter.pyに渡す
- 対応添付形式: .xlsx / .xls / .doc / .docx / .pdf

### ルートC: 手動実行
```bash
python attachment_importer/importer.py \
  --text "人員情報テキスト" \
  --file path/to/skillsheet.xlsx \
  --source "松野LINE"
```
または
```bash
python attachment_importer/importer.py \
  --text "人員情報テキスト" \
  --spreadsheet-url "https://docs.google.com/spreadsheets/d/xxx" \
  --source "松野メール"
```

---

## 処理フロー

```
1. テキスト解析（text_parser.py）
   ↓
2. 人員ブロック分割 → N人分のレコード生成
   ↓
3. ファイル解析（file_parser.py）
   ↓
4. テキスト情報 + ファイル情報をマージ（氏名マッチング）
   ↓
5. Notion重複チェック + 登録/更新（notion_writer.py）
   ↓
6. スキル○×判定はmatching_v2実行時にスキルシート原文から判定
   ↓
7. 結果をログ出力
```

---

## Step 1: テキスト解析（text_parser.py）

### 人員ブロック分割ロジック
区切り線パターンで分割する:
```python
DELIMITER_PATTERNS = [
    r'-{10,}',      # ----------
    r'ー{5,}',      # ーーーーー
    r'━{5,}',       # ━━━━━
    r'={10,}',      # ==========
]
```

分割後、各ブロックに「氏名」らしき文字列が含まれるブロックのみ人員情報として扱う。
氏名判定: 「氏名」「名前」「■名前」「【名前】」等のラベル、またはイニシャルパターン [A-Z]\.[A-Z]

### Claude APIによる構造化抽出
各ブロックをClaude APIに渡し、以下のJSONを返させる:

```
system: "人員情報テキストを解析してJSON形式で返してください。JSONのみ、マークダウン不要。"

user: """
以下の人員情報テキストから構造化データを抽出してください。
不明な項目はnullにしてください。

{text}

返すJSON:
{
  "name": "氏名（フルネームまたはイニシャル）",
  "age": 年齢（数値またはnull）,
  "gender": "男性/女性/null",
  "nearest_station": "最寄り駅",
  "affiliation": "所属会社名（弊社/当社は送信元会社名に置き換え）",
  "price": 単価（万円、数値のみ、例: 65）,
  "available_date": "稼働可能日（YYYY-MM-DD形式、即日は今日の日付）",
  "skills_list": ["Java", "Python", ...],
  "experience_years": 経験年数（数値またはnull）,
  "contact_email": "メールアドレスまたはnull",
  "contact_phone": "電話番号またはnull",
  "remote_preference": "リモート希望/常駐可/併用可/null",
  "raw_text": "このブロックの原文全体"
}
"""
```

---

## Step 2: ファイル解析（file_parser.py）

### 対応形式と処理方法

| 形式 | 処理方法 |
|---|---|
| .xlsx / .xls | openpyxlで全シートのテキストを抽出 |
| .docx / .doc | python-docxで全段落・テーブルのテキストを抽出 |
| .pdf | pdfplumberで全ページテキストを抽出 |
| Googleスプレッドシート URL | drive_downloader.pyでExcelとしてDL → openpyxlで処理 |

### テキスト抽出後の処理
抽出した全テキストをClaude APIに渡して構造化（text_parserと同じプロンプト）。
ファイルに複数人が含まれる場合は複数レコードを返す（リスト形式）。

### Googleスプレッドシートのダウンロード
```python
# URLからファイルIDを抽出してExportエンドポイントでDL
# https://docs.google.com/spreadsheets/d/{FILE_ID}/export?format=xlsx
# 認証不要の公開スプレッドシートはそのままDL
# 要認証の場合はDriveリンクURLフィールドにURLだけ保存して終了
```

---

## Step 3: テキスト+ファイル情報のマージ

### 氏名マッチングロジック
- テキスト解析結果のnameとファイル解析結果のnameを照合
- 完全一致 > イニシャル一致 > 部分一致 の順で突合
- 突合できた場合: ファイル情報優先でテキスト情報を補完
- 突合できない場合: テキスト情報のみでNotionに登録（ファイルは別途DriveリンクURLに保存）

---

## Step 4: Notion登録（notion_writer.py）

### 重複チェック
エンジニアDBを「名前」で検索し、同名レコードが存在する場合は更新（上書き）。
存在しない場合は新規作成。

### 登録フィールドマッピング

| Notionフィールド | ソース |
|---|---|
| 名前（title） | マージ結果.name |
| スキル（multi_select） | マージ結果.skills_list（DBに存在するオプションのみ） |
| 単価（万円） | マージ結果.price |
| 稼働可能日 | マージ結果.available_date |
| 最寄り駅 | マージ結果.nearest_station |
| 所属会社名 | マージ結果.affiliation |
| 所属会社 | マージ結果.affiliation |
| 入力元 | 引数sourceの値（松野LINE/岡本LINE/松野メール等） |
| 人員情報原文 | マージ結果.raw_text（テキストブロック原文） |
| 添付ファイルパス | ローカル保存パス（Excel/Word/PDFの場合） |
| DriveリンクURL | GoogleスプレッドシートURL（スプレッドシートの場合） |
| 経験年数 | マージ結果.experience_years |
| イニシャル | 氏名からイニシャル自動生成（例: H.S） |
| メール | マージ結果.contact_email |
| 連絡先 | マージ結果.contact_phone |
| 担当者 | sourceから自動判定（松野→松野、岡本→岡本、共通→共通） |
| 稼働状況 | デフォルト「稼働可能」 |

### スキルのmulti_selectマッピング
DBに存在しないスキル名は登録できないため、Claude APIで既存オプション名に変換する。
変換できないスキルは「備考（LINEメモ）」に追記。

既存スキルオプション（エンジニアDB確認済み）:
Java, Python, PHP, JavaScript, TypeScript, C#, Node.js, React, AWS, インフラ,
PostgreSQL, Oracle, Vue.js, MySQL, Swift, Azure, Linux, Go, Ruby, Docker, MongoDB,
Spring, SQL Server

---

## matching_v2のskill_judge.py修正

### 現状
Notionの`スキル`（multi_select）フィールドのみ参照。

### 修正後: スキル情報の参照優先順位
1. `添付ファイルパス` があれば → ファイルを読んでフルテキストで判定
2. `DriveリンクURL` があれば → スプレッドシートを読んでフルテキストで判定
3. `人員情報原文` があれば → 原文テキストで判定
4. いずれもなければ → `スキル`（multi_select）のみで判定（現状維持）

この変更により「スキルシートを読んで○×を出す」が実現する。
skill_judge.pyにfile_parser.pyのテキスト抽出関数をimportして使用する。

---

## mail_pipeline.pyへの追加

mail_pipeline.pyの classify_email() で人員情報メールを検出した場合に
attachment_importer/importer.py をサブプロセスで呼び出す。

```python
if email_type in ["人員情報", "人材紹介"] and attachment_paths:
    for path in attachment_paths:
        subprocess.Popen([
            sys.executable,
            "attachment_importer/importer.py",
            "--text", email_body,
            "--file", path,
            "--source", source_label,
        ], cwd=SES_WORK_DIR)
```

---

## エラーハンドリング

| エラー | 対応 |
|---|---|
| ファイル解析失敗 | テキスト情報のみで登録、ログに記録 |
| Claude API失敗 | リトライ3回、失敗時はスキルフィールド空欄で登録 |
| Notion登録失敗 | ログに記録、failed_imports.jsonに保存 |
| スプレッドシートDL失敗 | URLのみNotionに保存して終了 |
| 30分以内にファイルなし | pendingを破棄してログに記録 |

---

## ログ出力

ses_work/attachment_importer/import.log:
```
[2026-05-26 12:00:00] [SUCCESS] H.S → 新規登録 スキル: Java, JavaScript, Spring
[2026-05-26 12:00:01] [SUCCESS] OA → 更新 スキル: Java, C#, React
[2026-05-26 12:00:02] [WARN] U.H → ファイル突合失敗、テキストのみ登録
[2026-05-26 12:00:03] [ERROR] ファイル解析失敗: skillsheet.xlsx → テキスト情報のみで登録
```

---

## 依存ライブラリ

```
openpyxl       # Excel読み取り
python-docx    # Word読み取り
pdfplumber     # PDF読み取り
anthropic      # Claude API（スキル抽出）
requests       # Notion API / HTTP
python-dotenv  # .env読み込み
```

インストール:
```bash
pip install openpyxl python-docx pdfplumber anthropic requests python-dotenv --break-system-packages
```

---

## 変更履歴

| 日付 | 内容 |
|---|---|
| 2026-05-26 | v1初版作成 |
