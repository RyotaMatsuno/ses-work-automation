# 【Cursor作業指示】Week1 Task B: Notion登録失敗リトライ＋processed管理修正

対象ディレクトリ: ses_work/mail_pipeline/
作業内容: 案件データ永久欠損の防止
完了条件: 修正＋テスト追加＋既存テスト全パス
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 修正1: register_project()をcommon/notion_register.pyに委譲

### 問題
mail_pipeline.py の register_project() は429リトライなし・timeout未指定・重複チェックなし。
一方 common/notion_register.py には429リトライ＋upsertが実装済みだが未使用。

### 修正方針
1. mail_pipeline.py の register_project() 内のNotion API呼び出しを
   common.notion_register.register_project() に委譲
2. properties組み立てロジックは mail_pipeline.py に残す
3. 429リトライ、案件名+入力元でupsert、timeout=30s が自動適用される

---

## 修正2: Notion登録失敗時のprocessed管理修正

### 問題
finally節で無条件にsave_processed_id()を実行 → 登録失敗でもprocessed=1 → 再処理不可

### 修正方針
```python
notion_success = False
try:
    classify_result = classify_email_v2(...)
    update_classify_result(msg_id, classify_result)
    if classify_result == "project":
        notion_success = register_project(info, ...)
        if notion_success:
            # 後続処理
            ...
    else:
        notion_success = True
except Exception as e:
    log(f"処理エラー: {e}")
    import traceback
    log(traceback.format_exc())
finally:
    if notion_success:
        save_processed_id(msg_id)
    else:
        log(f"Notion登録未完了のため再処理対象: {msg_id}")
```

### 無限再処理ループ防止
raw_inbox.py に retry_count カラム追加。
retry_count >= 3 の場合は processed=1 にして諦める（ログ+LINE通知）。

### テスト追加
- Notion登録成功時: processed=1
- Notion登録失敗時: processed=0（再処理対象）
- retry_count >= 3: processed=1 + 警告ログ

---

## 共通ルール
- 既存テスト全パス / 新規コードにtype hint
