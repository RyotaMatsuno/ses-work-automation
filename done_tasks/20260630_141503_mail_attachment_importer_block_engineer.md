# 【Cursor作業指示】mail_attachment_importer: 人員登録パス完全禁止

## 対象ディレクトリ
ses_work/mail_attachment_importer/

## 背景
事業ルール: 「人員は松野/岡本がLINE経由で手動登録のみ」。
配信メール経由の人員は取り込まない。

現状: mail_attachment_importerが添付スキルシートを解析し、
classify_content() == "engineer" の場合にNotionエンジニアDBに登録している。
これにより、配信メールの人員が無差別にエンジニアDBに取り込まれている。

## 作業内容

### 1. importer.py 修正

#### process_attachments() (L93付近)
変更前:
```python
if content_type == "engineer":
    records = extract_engineers(text, filename)
    ...
    for eng in records:
        result = register_engineer(eng, meta)
```

変更後:
```python
if content_type == "engineer":
    logger.info(f"人員判定→スキップ（LINE手動登録のみ許可）: {filename}")
    stats["skip"] += 1
    continue
```

#### process_sheet_urls() (L118付近)
この関数は全体が人員登録用。関数内容を以下に置換:
```python
def process_sheet_urls(sheet_urls: list, meta: dict) -> dict:
    """パターンB/C: 廃止。人員はLINE手動登録のみ。""    logger.info(f"スプレッドシート人員登録パスは廃止済み。{len(sheet_urls)}件スキップ")
    return {"success": 0, "skip": len(sheet_urls), "error": 0}
```

#### main() (L264付近, L272付近)
パターンAのprocess_attachments呼び出しはそのまま（案件登録にも使う）。
パターンB/Cのprocess_sheet_urls呼び出しはそのまま（関数内でスキップする）。

### 2. ai_extractor.pyはclassify_content()を残す
- classify自体は残しておく（ログで人員メールのボリュームを監視できる）
- register_engineerの呼び出し側だけ止める

### 3. テスト
- DRY_RUN=1でimporter.pyを実行し、人員がスキップされることをログで確認
- 案件登録は影響なく動作することを確認

## 参照ファイル
- CLAUDE.md
- importer.py (修正対象)
- ai_extractor.py (参照のみ、無修正)

## 完了条件
- [ ] importer.pyでengineer判定時にNotion登録を行わずスキップする
- [ ] process_sheet_urls()が全件スキップを返す
- [ ] 案件登録パスは影響なし
- [ ] DRY_RUN=1でログ確認済み

## 質問がある場合
Claude.aiチャットに貼り付けて確認
