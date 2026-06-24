# 【Cursor作業指示】Task U: LINE人員登録パス修正（candidate_intake）

対象ディレクトリ: ses_work/line_webhook/ + ses_work/line_bridge/
作業内容: LINE経由の人員登録が「自動処理対象外」になるバグ修正
参照ファイル: CLAUDE.md / research_results/GPT_WALLHIT_LINE_REGISTRATION_20260622.md
完了条件: Google Sheets URL + 構造化テキストがエンジニア登録フローに正しくルーティング
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 背景
CEOがLINEにGoogle Sheets URL + 「【名前】Y.S...【単価】40万...」形式のメッセージを送った際、
line_bridge.pyのclassify_route()がURL検知せずにdevelopmentキーワードで分類し、
「自動処理対象外」として弾いた。エンジニアDBに登録されなかった。

## Phase 1: 再発防止（最小修正）

### 修正1: line_bridge.py classify_route() にURL/候補者先行検知

classify_route()の最上部（SKIP/IMMEDIATE判定の前）に追加:

```python
def classify_route(text: str) -> dict[str, str]:
    normalized = text.strip().lower()
    stripped = text.strip()
    
    # ★ URL + 候補者フォーマット検知（最優先）
    has_sheet_url = bool(re.search(r"https://docs\.google\.com/spreadsheets/", stripped))
    has_candidate_format = bool(re.search(r"【(?:名前|氏名|イニシャル)】", stripped))
    has_drive_url = bool(re.search(r"https://(?:docs|drive)\.google\.com/", stripped))
    
    if has_sheet_url or (has_drive_url and has_candidate_format) or has_candidate_format:
        return {
            "route": "candidate_intake",
            "kind": "engineer_registration",
            "assignee": "jobz",
            "human_confirmation": "不要",
        }
    
    # 以降は既存ロジック
    if _INITIAL_PLACE_RE.match(stripped):
        ...
```

### 修正2: line_bridge.py route_line_message() にcandidate_intakeハンドラ追加

```python
if route["route"] == "candidate_intake":
    # 本文から候補者情報を抽出
    eng_info = _parse_candidate_text(text)
    if eng_info:
        # 確認メッセージ付きでキュー登録
        return {
            "handled": True,
            "reply": f"候補者を検出しました。\n名前: {eng_info['name']}\n単価: {eng_info['price']}万\nスキル: {', '.join(eng_info['skills'][:5])}\n\nキューに登録しました。",
            "queue_task": {
                "kind": "engineer_registration",
                "assignee": "jobz",
                "input_data": json.dumps(eng_info, ensure_ascii=False),
            }
        }
```

### 修正3: 本文パーサー _parse_candidate_text() 追加

```python
def _parse_candidate_text(text: str) -> dict | None:
    # 【項目】値 形式を解析
    patterns = {
        "name": r"【(?:名前|氏名)】\s*(.+?)(?:
|【)",
        "age_gender": r"(\d+歳[/／]?(?:男性|女性))",
        "station": r"【(?:最寄|最寄り駅?)】\s*(.+?)(?:
|【)",
        "price": r"【(?:単価|希望単価)】\s*(\d+)万",
        "start_date": r"【(?:開始日?|稼働)】\s*(.+?)(?:
|【)",
        "skills": r"【(?:スキル|技術)】\s*(.+?)(?:
|【)",
    }
    result = {}
    for key, pat in patterns.items():
        m = re.search(pat, text, re.DOTALL)
        if m:
            result[key] = m.group(1).strip()
    
    if not result.get("name"):
        return None
    
    # Skills分割
    if result.get("skills"):
        result["skills"] = [s.strip() for s in re.split(r"[,、/|]", result["skills"]) if s.strip()]
    
    # URL抽出
    url_m = re.search(r"https://(?:docs|drive)\.google\.com/[^\s]+", text)
    if url_m:
        result["sheet_url"] = url_m.group()
    
    return result
```

## Phase 2: 重複防止（同時実装）

### Notionエンジニア登録前の重複チェック

```python
def _check_duplicate_engineer(name: str, station: str) -> bool:
    # Notion APIで同名+同最寄りのエンジニアを検索
    resp = requests.post(
        f"https://api.notion.com/v1/databases/{ENGINEER_DB}/query",
        headers=headers,
        json={"filter": {"property": "名前", "title": {"equals": name}}, "page_size": 5}
    )
    for eng in resp.json().get("results", []):
        props = eng.get("properties", {})
        st = props.get("最寄り駅", {}).get("rich_text", [])
        existing_station = st[0].get("plain_text", "") if st else ""
        if station and station in existing_station:
            return True  # 重複
    return False
```

## テスト要件

### テスト1: classify_route
- "https://docs.google.com/spreadsheets/... 【名前】Y.S..." → candidate_intake
- "PH 京成小岩" → immediate/matching（既存動作維持）
- "バグ修正して" → development（既存動作維持）

### テスト2: _parse_candidate_text
- 「【名前】Y.S（33歳男性）
【最寄】船橋競馬場駅
【単価】40万」→ 正しく抽出
- URL付き → sheet_url抽出

### テスト3: 重複防止
- 同名+同最寄りが既にDBにある → 「既に登録済みです」

---

## 禁止事項
- webhook_server.pyのhandle_sheet_url()は変更しない（fallbackとして残す）
- 既存のマッチングフロー（PH 京成小岩等）を壊さない
- 候補者情報をメール送信しない
