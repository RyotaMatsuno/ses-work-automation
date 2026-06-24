# SPEC_cost_fix.md — mail_pipeline コスト修正仕様

作成: 2026-06-10（ジョブズ設計）

---

## 背景・問題

### バグ1: 非スキルシートPDFをsonnetで繰り返し処理

`mail_pipeline/mail_pipeline.py` の `fetch_email_body_and_attachments()` が
発注書・請求書・勤務表などの PDF を `is_skill_sheet=True` と判定し、
`process_skill_sheet()` → `extract_skills_from_image()` (VISION_MODEL=sonnet) を
30分ごとに毎回呼び出している。

**コスト影響:** sonnet が全コストの73%（$0.716 / 累計）を占める原因。

**根本原因:**
- `is_skill_sheet` 判定が `content_type` か拡張子が `.pdf` なら全て True になる
- 「スキルシートかどうか」を内容・ファイル名で判定していない
- `processed_ids` は最終的に `save_processed_id` が呼ばれるが、
  添付処理は判定前に走るため毎回sonnetを叩いてしまう

### バグ2: matching_v3 のコストログに model="model" が記録される

`matching_v3/config.py` が `common/model_config.py` から
`STRUCTURER_MODEL` を import して `DEFAULT_STRUCTURER_MODEL = STRUCTURER_MODEL` に
代入しているが、config/.env に `STRUCTURER_MODEL` キーが存在しない場合、
`model_config.py` のデフォルト (`"gpt-4.1-nano"`) が使われるはずが
`"model"` という文字列が返るケースがある。
cost_log に `model="model"` が2件残っており、コスト計算がデフォルトレートで
行われ過小計上になっている。

---

## 修正内容

### Fix1: mail_pipeline/mail_pipeline.py

**対象関数:** `fetch_email_body_and_attachments()` 内の `is_skill_sheet` 判定

**修正方針:** ファイル名ベースのスキルシート判定を追加。
発注書・請求書・勤務表などの業務文書をスキルシート処理から除外する。

```python
# 追加するスキップキーワード（ファイル名に含まれていたらスキップ）
SKIP_ATTACHMENT_KEYWORDS = (
    "発注書", "請求書", "注文書", "勤務表", "明細", "納品書",
    "契約書", "見積書", "領収書", "PO-", "invoice", "order",
)

def _is_skill_sheet_by_filename(filename: str) -> bool:
    """ファイル名からスキルシートかどうかを判定。業務文書はFalseを返す。"""
    if not filename:
        return True  # ファイル名不明は従来通り処理（保守的）
    lower = filename.lower()
    for kw in SKIP_ATTACHMENT_KEYWORDS:
        if kw.lower() in lower:
            return False
    return True
```

`is_skill_sheet` 判定を以下に変更:
```python
is_skill_sheet = (
    (content_type in SKILL_SHEET_MIME_TYPES or ext in SKILL_SHEET_EXTENSIONS)
    and _is_skill_sheet_by_filename(filename)  # ← 追加
)
```

### Fix2: matching_v3/config.py の model名バグ

`DEFAULT_STRUCTURER_MODEL` が空文字や `None` になるケースを防ぐ。

```python
# 変更前
DEFAULT_STRUCTURER_MODEL = STRUCTURER_MODEL

# 変更後
DEFAULT_STRUCTURER_MODEL = STRUCTURER_MODEL or "gpt-4.1-nano"
```

さらに `Config.__init__` の `structurer_model` セットも同様にフォールバック追加:
```python
self.structurer_model = (
    os.environ.get("STRUCTURER_MODEL")
    or self.env.get("STRUCTURER_MODEL")
    or DEFAULT_STRUCTURER_MODEL
    or "gpt-4.1-nano"
)
```

---

## 完了条件

1. `python -c "from mail_pipeline.mail_pipeline import fetch_email_body_and_attachments; print('OK')"` がエラーなしで通る
2. ファイル名に「発注書」「請求書」「勤務表」「注文書」「PO-」を含むPDFが `attachments` に追加されないこと（ユニットテストで確認）
3. `matching_v3/config.py` をインポートして `DEFAULT_STRUCTURER_MODEL` が `"gpt-4.1-nano"` であること
4. 既存テスト `pytest matching_v3/tests/ -v` が全パス

---

## 影響範囲

- `mail_pipeline/mail_pipeline.py`: `is_skill_sheet` 判定1箇所 + スキップ関数追加
- `matching_v3/config.py`: `DEFAULT_STRUCTURER_MODEL` 代入1行 + `structurer_model` セット1箇所

---

## 注意事項

- `processed_ids.json` の構造・書き込みロジックは変更しない
- `SKILL_SHEET_MIME_TYPES` / `SKILL_SHEET_EXTENSIONS` 定数は変更しない
- 「人材メールスキップ」（L1243-L1246）は変更しない
- エンコーディング: UTF-8、日本語パスを cwd に直接渡さない
---

## Gate①指摘への対応（2026-06-10）

### SKIP_ATTACHMENT_KEYWORDS 拡充
英語ファイル名の業務文書も除外対象に追加:
```python
SKIP_ATTACHMENT_KEYWORDS = (
    "発注書", "請求書", "注文書", "勤務表", "明細", "納品書",
    "契約書", "見積書", "領収書", "PO-", "invoice", "order",
    "contract", "statement", "receipt", "quotation", "delivery",
)
```

### ロールバック手順
- Fix1が問題を起こした場合: `mail_pipeline.py.bak_0602` を復元して再起動
  （`copy mail_pipeline\mail_pipeline.py.bak_0602 mail_pipeline\mail_pipeline.py`）
- Fix2が問題を起こした場合: `DEFAULT_STRUCTURER_MODEL = STRUCTURER_MODEL or "gpt-4.1-nano"` の `or "gpt-4.1-nano"` を削除

### 追加テストケース（TASKS.mdに反映済み）
- スキルシートファイル名（「田中太郎_スキルシート.pdf」「resume_suzuki.docx」）が True を返すこと
- CostGuard の `can_spend` が Fix1 適用後も変わらず呼ばれること（既存の `extract_skills_from_image` 内で呼ばれているため変更不要）
