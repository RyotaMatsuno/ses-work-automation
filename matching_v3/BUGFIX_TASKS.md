# matching_v3 バグ修正 TASKS

## 修正対象ファイルと修正内容

### 1. structurer.py の修正

#### 問題
- `_parse_json_or_fallback` 関数で、フェンス除去処理の実装が不完全
- `raw_important_notes` にフェンス除去前の生テキスト（`text[:500]`）を入れているため、
  フォールバック時に ````json\n{...` がそのまま保存される
- `max_tokens=1200` が不足しており、LLMの出力が途中で切れてJSONパース失敗になっている

#### 修正内容（structurer.py）
1. `_call_anthropic` の `max_tokens` を `1200` → `2000` に変更
2. `_parse_json_or_fallback` 関数を以下のように修正:
   - フェンス除去後のテキストを `stripped` 変数に入れる
   - `json.loads` は `stripped` に対して実行する
   - フォールバック時の `raw_important_notes` も `stripped[:500]` にする（フェンス除去済みテキスト）
   - 追加: `stripped` からJSONオブジェクト部分（`{`〜`}`）を正規表現で抽出して再パース試行する
     （途中切れ対策: `re.search(r'\{.*\}', stripped, re.DOTALL)` → `json.loads` ）
     ※ これが失敗してもフォールバックに進むだけでOK

修正後のコードイメージ:
```python
def _parse_json_or_fallback(text: str) -> dict[str, Any]:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r'^```(?:json)?\s*', '', t)
        t = re.sub(r'\s*```\s*$', '', t).strip()
    if not t:
        logger.warning("Structurer: empty response text")
        stripped = ""
    else:
        stripped = t

    # 通常パース
    try:
        data = json.loads(stripped)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        logger.warning("Structurer JSON parse failed (first 200 chars): %s", stripped[:200])

    # 途中切れ対策: JSONオブジェクト部分を正規表現で抽出して再パース
    m = re.search(r'\{.*\}', stripped, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group())
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    return {
        "role": None,
        "required_skills": [],
        ...（省略、既存と同じフォールバック値）
        "extraction_confidence": 0.0,
        "raw_important_notes": stripped[:500] if stripped else None,  # ← フェンス除去済みに変更
    }
```

### 2. matcher.py の修正

#### 問題
- `_days_since(last_edit) > 7` → エンジニア鮮度チェックが7日になっているが
  判断マニュアルの基準は「3週間（21日）」

#### 修正内容（matcher.py）
- `judge` 関数内の `if last_edit and _days_since(last_edit) > 7:` を
  `if last_edit and _days_since(last_edit) > 21:` に変更

### 3. processed_db.py または matching_v3.py の確認と修正

#### 問題
- phase0_emails.jsonl には100件の案件があるのに、structured.jsonl には202件ある
  → 同一案件が2回structureされている（重複実行）
- processed_db がphase0実行時に機能していない可能性

#### 修正内容
- `matching_v3.py` または `phase0_runner` に該当する処理を確認
- phase0の実行時に `processed_db` でcase_idの重複チェックをしているか確認
- 重複チェックしていなければ追加する（同じcase_idは1回だけstructureする）

## 実行順序
1. matcher.py の `> 7` → `> 21` を修正
2. structurer.py を修正（max_tokens + フォールバック改善）
3. 既存テスト（pytest）を実行して全パスを確認
4. 完了したらこのファイルに [DONE] を追記

## 注意事項
- SPEC.md / CLAUDE.md / TASKS.md のルールに従うこと
- 既存テストを壊さないこと
- credentials / APIキーを変更しないこと

[DONE] 2026-06-03
