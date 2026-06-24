# SPEC_v4_diff.md — mail_attachment_importer 差分修正仕様
# 既存実装への追加・修正のみ。スクラッチ実装禁止。

content = """# SPEC v4 差分修正仕様 — mail_attachment_importer

最終更新: 2026-05-26

## 前提
既存のmail_attachment_importerは人員取り込みが完成済み（v3）。
今回は以下3点のみ修正する。スクラッチ実装・既存動作の破壊は禁止。

---

## 修正1: importer.py — 添付ファイルの人員/案件自動判定

### 問題
現状の process_attachments() は添付を全て extract_engineers() に渡している。
案件情報の添付（Excel/Word/PDF）がエンジニアとして登録されてしまう。

### 修正内容
ai_extractor.py に classify_content() 関数を追加し、
添付テキストが「人員」か「案件」かをClaude APIで判定してから
それぞれの処理に振り分ける。

#### ai_extractor.py に追加する関数

```python
CLASSIFY_SYSTEM_PROMPT = \"\"\"あなたはSES業界のメール添付ファイルの内容を分類するAIです。
以下のテキストが「人員情報（スキルシート・経歴書）」か「案件情報（募集要項）」かを判定してください。
以下のJSONのみを返してください（説明文不要）:
{"type": "engineer"} または {"type": "project"} または {"type": "unknown"}

判断基準:
- 人員: 氏名・経験年数・スキル・稼働可能日・希望単価が主体
- 案件: 業務内容・必須スキル・期間・勤務地・募集単価が主体
\"\"\"

def classify_content(text: str) -> str:
    \"\"\"
    テキストが人員情報か案件情報かを分類。
    Returns: "engineer" / "project" / "unknown"
    \"\"\"
    import anthropic, json, os
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return "unknown"
    client = anthropic.Anthropic(api_key=api_key)
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=50,
            system=CLASSIFY_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": text[:3000]}]
        )
        raw = response.content[0].text.strip()
        data = json.loads(raw)
        return data.get("type", "unknown")
    except Exception as e:
        logger.error(f"classify_content失敗: {e}")
        return "unknown"
```

#### importer.py の process_attachments() 修正

```python
def process_attachments(attachments: list, meta: dict) -> dict:
    from file_parser import parse_file
    from ai_extractor import extract_engineers, extract_projects, classify_content
    from notion_writer import register_engineer, register_project

    stats = {"success": 0, "skip": 0, "error": 0}

    for att in attachments:
        filename = att["filename"]
        ext = att["ext"]
        file_data = att["data"]

        text = parse_file(filename, ext, file_data)
        if not text or len(text.strip()) < 200:
            logger.warning(f"テキスト変換失敗または短すぎ: {filename} → スキップ")
            stats["error"] += 1
            continue

        # 人員 or 案件を自動判定
        content_type = classify_content(text)
        logger.info(f"コンテンツ判定: {filename} → {content_type}")

        if content_type == "engineer":
            records = extract_engineers(text, filename)
            for eng in records:
                result = register_engineer(eng, meta)
                stats["success" if result else "skip"] += 1

        elif content_type == "project":
            records = extract_projects(text, filename)
            for proj in records:
                result = register_project(proj, meta)
                stats["success" if result else "skip"] += 1

        else:
            logger.warning(f"判定不能のためスキップ: {filename}")
            stats["skip"] += 1

    return stats
```

---

## 修正2: mail_fetcher.py — matsuno / okamoto アカウント追加

### 問題
現状は sessales のみ対応。matsuno / okamoto からの添付メールが未処理。

### 修正内容
config/.env から以下を読む（既存のmail_pipeline.pyと同じキー名を使う）:
- IMAP_HOST / IMAP_PORT（共通）
- MATSUNO_EMAIL / MATSUNO_PASSWORD
- OKAMOTO_EMAIL / OKAMOTO_PASSWORD
- SESSALES_EMAIL / SESSALES_PASSWORD（既存）

fetch_new_emails() を以下のように修正:
- デフォルトで3アカウント全て処理
- --account オプション（sessales/matsuno/okamoto/all）で絞り込み可能
- アカウントごとに processed_ids.json のキーを分ける
  例: {"sessales": [1,2,3], "matsuno": [4,5], "okamoto": [6]}

#### processed_ids.json 形式変更
既存の flat list → dict 形式に移行
移行処理: 既存がlistなら sessales キーに移す

```python
def load_processed_ids() -> dict:
    try:
        with open(PROCESSED_IDS_PATH, "r") as f:
            data = json.load(f)
            # 後方互換: 旧フォーマット(list)をdictに変換
            if isinstance(data, list):
                return {"sessales": data, "matsuno": [], "okamoto": []}
            return data
    except Exception:
        return {"sessales": [], "matsuno": [], "okamoto": []}

def save_processed_id(uid: str, account: str = "sessales"):
    ids = load_processed_ids()
    if account not in ids:
        ids[account] = []
    if uid not in ids[account]:
        ids[account].append(uid)
    with open(PROCESSED_IDS_PATH, "w") as f:
        json.dump(ids, f)
```

---

## 修正3: ai_extractor.py — モデル変更

### 問題
現状 claude-sonnet-4-5 を使用。haiku で十分かつコスト1/5。

### 修正内容
extract_engineers() / extract_projects() 両方のモデルを
claude-haiku-4-5-20251001 に変更。

---

## 修正4: importer.py — meta に account フィールド追加

メール送信元アカウントを meta に追加して Notion の備考に記録する。
```python
meta = {
    "subject": subject,
    "from": mail_item["from"],
    "date": mail_item["date"],
    "account": account_name,  # "sessales" / "matsuno" / "okamoto" を追加
}
```

---

## TASKS.md 更新内容（Codexが完了時に更新すること）

```
## Phase 8: v4差分修正（2026-05-26）
- [ ] 8-1. ai_extractor.py に classify_content() 追加
- [ ] 8-2. ai_extractor.py のモデルを claude-haiku-4-5-20251001 に変更
- [ ] 8-3. importer.py の process_attachments() を人員/案件自動判定に修正
- [ ] 8-4. mail_fetcher.py に matsuno / okamoto アカウント追加
- [ ] 8-5. processed_ids.json をdict形式に移行（後方互換処理込み）
- [ ] 8-6. importer.py の meta に account フィールド追加
- [ ] 8-7. 動作確認: python -c "from ai_extractor import classify_content; print(classify_content('氏名: 山田太郎 スキル: Java'))"
- [ ] 8-8. 動作確認: python -c "from ai_extractor import classify_content; print(classify_content('必須スキル: Java 勤務地: 東京 期間: 6ヶ月'))"
- [ ] 8-9. 動作確認: DRY_RUN=1 python importer.py で3アカウントのIMAP接続確認
```

---

## 禁止事項
- 既存の register_engineer() / register_project() の変更
- 既存の sheet_fetcher.py / file_parser.py の変更
- processed_ids.json の既存データ消去
- .bak なしで既存ファイルを上書き（.bak_0526 を先に作成すること）
"""

with open(
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_attachment_importer\SPEC_v4_diff.md", "w", encoding="utf-8"
) as f:
    f.write(content)
print("SPEC_v4_diff.md 書き込み完了", flush=True)
