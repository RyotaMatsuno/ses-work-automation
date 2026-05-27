import os
os.makedirs(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pipeline_notify_fix', exist_ok=True)

claude_md = r"""# CLAUDE.md - mail_pipeline + notify_line 修正

## 作業ディレクトリ
C:\Users\ma_py\OneDrive\Desktop\ses_work\  (OneDrive\デスクトップ\ses_work)

## 修正対象ファイル
1. mail_pipeline\mail_pipeline.py
2. matching_v2\notify_line.py
3. matching_v2\matching_v2.py

## 禁止事項
- LINEへの実際の送信（dry-runのみで確認）
- APIキーのハードコード（config/.envから読む）
- .bak_* ファイルの変更

## 文字コード
UTF-8必須
"""

spec_md = r"""# SPEC: mail_pipeline + notify_line 元データ転送・添付対応

## 目的
1. mail_pipeline: 1日400件以上の案件メールを全件処理できるよう上限を撤廃
2. notify_line: マッチング結果LINEに「元テキスト全文」を含める
3. notify_line: 添付ファイル（PDF/docx/xlsx）をLINEに転送する

---

## 修正1: mail_pipeline.py — 全件処理化

### 変更箇所
ファイル: ses_work/mail_pipeline/mail_pipeline.py

```python
# 変更前
FETCH_LIMIT = 50
PROCESS_LIMIT = 20

# 変更後
FETCH_LIMIT = 500
PROCESS_LIMIT = 500
```

また、fetch_recent_emails()のIMAP検索を「直近N件」ではなく
「当日分（SINCE today）+ 未処理IDのみ」に変更する。

```python
def fetch_recent_emails(limit: int = 500):
    import email.utils
    today_str = datetime.now().strftime("%d-%b-%Y")  # 例: 27-May-2026
    status, messages = mail.search(None, f'SINCE {today_str}')
    # 全IDを取得してprocessed_idsと差分だけ処理
```

ただし「SINCEで当日分だけ」だと古い未処理メールが取りこぼれるため、
processed_ids.jsonにないIDを全て対象にするフォールバックを残す。

---

## 修正2: result.json スキーマ拡張 — raw_body / attachments保存

### 変更箇所
ファイル: ses_work/matching_v2/matching_v2.py

マッチング結果の result.json に以下フィールドを追加する。

```json
{
  "project_id": "...",
  "project_name": "...",
  "project_url": "...",
  "raw_body": "メールやLINEで受信した元テキスト全文",
  "attachments": [
    {
      "filename": "スキルシート_田中.docx",
      "data_b64": "base64エンコードされたバイナリ",
      "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    }
  ],
  "candidates": [...]
}
```

取得元: Notionの「備考（LINEメモ）」フィールドまたは「案件詳細」フィールドから raw_body を取得。
添付ファイルは現状 result.json には含まれていないため、
matching_v2.pyでNotionページの「備考（LINEメモ）」に保存されているraw_bodyを引く。

実装方針:
- matching_v2.pyでNotionから案件を取得する際、「案件詳細」または「備考（LINEメモ）」を
  raw_body としてresult.jsonに追加保存する。
- 添付ファイルのバイナリはresult.jsonには入れない（サイズ大）。
  代わりに ses_work/mail_pipeline/pipeline_drafts/ に保存されている
  添付ファイルのパスをattachment_pathsとしてresult.jsonに記録する。

---

## 修正3: notify_line.py — 元テキスト全文をLINE通知に含める

### 変更箇所
ファイル: ses_work/matching_v2/notify_line.py

build_project_message() に以下を追加:

```python
# 元テキスト全文（raw_body）
raw_body = item.get("raw_body", "")
if raw_body:
    # LINEの1メッセージ上限は5000文字
    # raw_bodyが長い場合は先頭2000文字を表示
    body_preview = raw_body[:2000]
    lines.append("──────────────")
    lines.append("【元データ全文】")
    lines.append(body_preview)
    if len(raw_body) > 2000:
        lines.append(f"... (全{len(raw_body)}文字、省略)")
```

---

## 修正4: notify_line.py — 添付ファイルをLINEに送付

### LINE Messaging API ファイル送信の実装

LINEのpush_messageをテキスト + ファイルの複数メッセージに拡張する。

```python
def push_file_message(channel_token: str, user_id: str, filepath: str):
    """
    LINEにファイルを送信する。
    LINE Messaging API: https://api.line.me/v2/bot/message/push
    ファイル送信は「image」typeまたは「flex」+「uploadRichMenuImage」ではなく、
    LINE公式のドキュメントではPDF/Docxの直接送信はサポートされていない。
    
    代替案: ファイルをテキストで案内（ファイル名のみ通知）
    または: ファイルをCloudStorageにアップロードしてURLで共有
    
    現実的な実装: 添付ファイル名と内容のテキスト抽出をLINEメッセージに含める
    """
```

**重要制約**: LINE Messaging APIはPDF/Docxファイルの直接送信をサポートしていない。
「image」メッセージはJPG/PNG/GIFのみ。

実現可能な実装:
A. 添付ファイルのテキスト内容を抽出してLINEメッセージに含める（mail_pipeline.pyのskill_readerを流用）
B. ファイル名のみ通知 + pipeline_drafts/のパスを記載

本SPECではAを採用する:
- PDF/docx → テキスト抽出 → LINEメッセージの末尾に追記
- 抽出テキストは先頭1500文字まで

```python
def extract_attachment_text(attachment_path: str) -> str:
    """添付ファイルからテキストを抽出してLINEメッセージ用文字列を返す"""
    ext = Path(attachment_path).suffix.lower()
    try:
        if ext == '.pdf':
            data = open(attachment_path, 'rb').read()
            return extract_text_from_pdf(data)[:1500]
        elif ext in ('.docx', '.doc'):
            data = open(attachment_path, 'rb').read()
            return extract_text_from_docx(data)[:1500]
        elif ext in ('.txt',):
            return open(attachment_path, encoding='utf-8', errors='replace').read()[:1500]
    except Exception as e:
        return f"(テキスト抽出失敗: {e})"
    return ""
```

---

## result.jsonのraw_bodyを matching_v2.py で埋める方法

matching_v2.pyでNotionからページを取得する際、
「案件詳細」「備考（LINEメモ）」フィールドを raw_body として取得し、
result.jsonの各itemに追加する。

```python
# matching_v2.pyのfetch_projects()内
raw_body = get_text_property(props, "案件詳細") or get_text_property(props, "備考（LINEメモ）") or ""
project["raw_body"] = raw_body
```

---

## 完了条件
1. mail_pipeline.py: FETCH_LIMIT=500, PROCESS_LIMIT=500 に変更済み
2. mail_pipeline.py: IMAP検索がSINCE当日分を対象にする（processed_ids差分処理維持）
3. matching_v2.py: result.jsonのitemにraw_bodyフィールドが含まれる
4. notify_line.py: build_project_message()がraw_bodyを表示する
5. notify_line.py: build_project_message()がengineer側のraw_body（備考（LINEメモ））も表示する
6. python -m matching_v2.matching_v2 実行後のresult.jsonにraw_bodyが含まれること
7. python matching_v2/notify_line.py --dry-run が正常終了すること
"""

tasks_md = r"""# TASKS.md - mail_pipeline + notify_line 修正

## タスクリスト

- [ ] 1. mail_pipeline.py: FETCH_LIMIT=500, PROCESS_LIMIT=500 に変更
- [ ] 2. mail_pipeline.py: fetch_recent_emails() にSINCE当日検索を追加（processed_ids差分維持）
- [ ] 3. matching_v2.py: fetch_projects()でraw_bodyを取得してresult.jsonに追加
- [ ] 4. matching_v2.py: fetch_engineers()でraw_body（備考LINEメモ）を取得してresult.jsonに追加
- [ ] 5. notify_line.py: get_page_info()の"project"ブロックにraw_bodyフィールドを追加
- [ ] 6. notify_line.py: get_page_info()の"engineer"ブロックにraw_body（備考LINEメモ）を追加
- [ ] 7. notify_line.py: empty_page_info()に対応するraw_bodyキーを追加
- [ ] 8. notify_line.py: build_project_message()にraw_body表示セクションを追加（先頭2000文字）
- [ ] 9. notify_line.py: candidateのengineer raw_bodyも表示する
- [ ] 10. py_compile mail_pipeline/mail_pipeline.py → エラーなし
- [ ] 11. py_compile matching_v2/matching_v2.py → エラーなし
- [ ] 12. py_compile matching_v2/notify_line.py → エラーなし
- [ ] 13. python -m matching_v2.matching_v2 実行→result.jsonにraw_bodyが存在することを確認
- [ ] 14. python matching_v2/notify_line.py --dry-run → 正常終了・raw_body表示を確認
"""

base = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pipeline_notify_fix'
import os
os.makedirs(base, exist_ok=True)

for fname, content in [('CLAUDE.md', claude_md), ('SPEC.md', spec_md), ('TASKS.md', tasks_md)]:
    with open(os.path.join(base, fname), 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'written: {fname}')
