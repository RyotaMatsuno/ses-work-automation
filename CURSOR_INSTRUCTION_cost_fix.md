【Cursor作業指示】 — コストバグ修正（2026-06-10）
対象ディレクトリ: ses_work/
参照ファイル: SPEC_cost_fix.md / TASKS_cost_fix.md / CLAUDE.md
完了条件: TASKS_cost_fix.md の全チェックボックスが [x] になること

---

## Fix1: mail_pipeline/mail_pipeline.py

### 手順1: SKIP_ATTACHMENT_KEYWORDS 定数を追加
ファイル内の `SKILL_SHEET_EXTENSIONS` 定数の直後に以下を追加:

```python
SKIP_ATTACHMENT_KEYWORDS = (
    "発注書", "請求書", "注文書", "勤務表", "明細", "納品書",
    "契約書", "見積書", "領収書", "PO-", "invoice", "order",
    "contract", "statement", "receipt", "quotation", "delivery",
)
```

### 手順2: _is_skill_sheet_by_filename 関数を追加
`SKIP_ATTACHMENT_KEYWORDS` 定数の直後に以下の関数を追加:

```python
def _is_skill_sheet_by_filename(filename: str) -> bool:
    """ファイル名から業務文書（発注書・請求書等）を除外する。
    ファイル名不明の場合は保守的にTrueを返す。"""
    if not filename:
        return True
    lower = filename.lower()
    for kw in SKIP_ATTACHMENT_KEYWORDS:
        if kw.lower() in lower:
            return False
    return True
```

### 手順3: is_skill_sheet 判定を修正
L364付近の以下のコードを:
```python
is_skill_sheet = (
    content_type in SKILL_SHEET_MIME_TYPES or
    ext in SKILL_SHEET_EXTENSIONS
)
```
以下に変更:
```python
is_skill_sheet = (
    (content_type in SKILL_SHEET_MIME_TYPES or ext in SKILL_SHEET_EXTENSIONS)
    and _is_skill_sheet_by_filename(filename)
)
```

### 手順4: 動作確認
```
python -c "
import sys, os
sys.path.insert(0, '.')
from mail_pipeline.mail_pipeline import _is_skill_sheet_by_filename
assert not _is_skill_sheet_by_filename('発注書_PO-001.pdf'), 'FAIL: 発注書がTrueになっている'
assert not _is_skill_sheet_by_filename('invoice_2026.pdf'), 'FAIL: invoiceがTrueになっている'
assert _is_skill_sheet_by_filename('田中太郎_スキルシート.pdf'), 'FAIL: スキルシートがFalseになっている'
assert _is_skill_sheet_by_filename('resume_suzuki.docx'), 'FAIL: resumeがFalseになっている'
assert _is_skill_sheet_by_filename(''), 'FAIL: 空文字がFalseになっている'
print('Fix1 OK')
"
```

---

## Fix2: matching_v3/config.py

### 手順1: DEFAULT_STRUCTURER_MODEL のフォールバック追加
L28の以下を:
```python
DEFAULT_STRUCTURER_MODEL = STRUCTURER_MODEL
```
以下に変更:
```python
DEFAULT_STRUCTURER_MODEL = STRUCTURER_MODEL or "gpt-4.1-nano"
```

### 手順2: Config.__init__ の structurer_model セットを修正
L39-L42の以下を:
```python
self.structurer_model = os.environ.get(
    "STRUCTURER_MODEL",
    self.env.get("STRUCTURER_MODEL") or DEFAULT_STRUCTURER_MODEL,
)
```
以下に変更:
```python
self.structurer_model = (
    os.environ.get("STRUCTURER_MODEL")
    or self.env.get("STRUCTURER_MODEL")
    or DEFAULT_STRUCTURER_MODEL
    or "gpt-4.1-nano"
)
```

### 手順3: 動作確認
```
cd matching_v3
python -c "
from config import DEFAULT_STRUCTURER_MODEL, Config
assert DEFAULT_STRUCTURER_MODEL == 'gpt-4.1-nano', f'got [{DEFAULT_STRUCTURER_MODEL}]'
cfg = Config()
assert cfg.structurer_model, 'structurer_model が空'
print('Fix2 OK:', cfg.structurer_model)
"
```

---

## 最終確認

```
cd matching_v3
python -m pytest tests/ -v
```
全パスを確認してTASKS_cost_fix.md を更新すること。

質問がある場合: Claude.aiチャットに貼り付けて確認
