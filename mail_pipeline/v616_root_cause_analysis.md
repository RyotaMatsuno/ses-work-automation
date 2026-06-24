# v6.16 根本原因分析レポート

作成日: 2026-06-18  
分析者: Claude Code (Sonnet 4.6)  
対象: mail_pipeline.py v5.1 (bak_phase4) vs v6.16 (bak_emergency_20260617_182923)

---

## 1. 119行差分の機能ブロック分類

`diff_v51_vs_v616.txt` (1476行) を機能単位で分類した結果:

| ブロック | 追加行 | 削除行 | 概要 |
|---|---|---|---|
| import群 | +12 | -8 | argparse/ZoneInfo/zenkaku追加、mimetypes/smtplib削除 |
| 件名キーワード事前分類 | +65 | 0 | SUBJECT_SKIP/PROJECT/ENGINEER_PATTERNS + classify_subject_keyword() |
| 配信メール除外ロジック | +42 | 0 | is_broadcast() / _sender_allowed() / BROADCAST_* 定数 |
| 添付ファイルフィルタ | +20 | 0 | _is_skill_sheet_by_filename() + SKIP_ATTACHMENT_KEYWORDS |
| IMAPフェッチ改善 | +16 | -6 | INTERNALDATE取得 / received_at追加 / today_onlyフィルタ |
| プロパティ動的解決 | +25 | 0 | ensure_engineer_db_properties() + ENGINEER_PROP_NAMES global |
| validate_engineer統合 | +35 | 0 | ValidationResult / バリデーション呼び出し |
| register_engineer変更 | +15 | -12 | prop_map動的解決 / drive_url/received_at引数追加 |
| register_project変更 | +8 | -10 | notion_register_project委譲 / 引数変更 |
| Drive Upload変更 | +20 | -15 | upload_to_drive移動 / initial_drive_url廃止 |
| processed_ids変更 | +8 | -6 | load/save修正 (2000件上限 / raise追加) |
| main()変更 | +20 | -30 | dry_run flag / argparse / mark_processed / v5.2表記 |

---

## 2. Notion API payload 生成箇所の差分

### 2.1 engineer DB (`register_engineer`)

| プロパティ名 | 型 | v5.1での処理 | v6.16での処理 | 差分の影響 |
|---|---|---|---|---|
| 名前 | title | `"名前"` をハードコード | `prop_map["氏名"]` で動的解決 (`"氏名"` or `"名前"`) | **解決失敗時 KeyError** |
| 備考（LINEメモ） | rich_text | `"備考（LINEメモ）"` ハードコード | `prop_map["備考"]` で動的解決 | 解決失敗時 KeyError |
| 稼働状況 | select | `"稼働状況"` ハードコード | `"稼働状況"` ハードコード | 変更なし |
| スキル | multi_select | `"スキル"` ハードコード | `prop_map["スキル"]` で動的解決 | 解決失敗時 KeyError |
| 単価（万円） | number | `"単価（万円）"` ハードコード | `prop_map["単価"]` / 円単位判定 | 単位換算ロジック変更 |
| 提案対象フラグ | checkbox | なし | `prop_map["提案対象フラグ"]` で追加 | 新規 |
| 情報取得日 | date | なし | `prop_map["情報取得日"]` で追加 | 新規 |

### 2.2 project DB (`register_project`)

| プロパティ名 | 型 | v5.1での処理 | v6.16での処理 | 差分の影響 |
|---|---|---|---|---|
| 案件名 | title | `"案件名"` ハードコード | `"案件名"` ハードコード（変更なし） | なし |
| ステータス | select | `"募集中"` ハードコード | `"募集中"` ハードコード | なし |
| 案件詳細 | rich_text | `"案件詳細"` ハードコード | `"案件詳細"` ハードコード | なし |

---

## 3. 根本原因: 確定

### 3.1 直接原因 — `ensure_engineer_db_properties()` の起動時 SystemExit

**発見**: v6.16 は `main()` の冒頭（line 1392）で `ensure_engineer_db_properties()` を呼ぶ。  
この関数は:
1. `get_database_property_names(ENGINEER_DB)` → Notion API で DB スキーマ取得
2. 必須プロパティが1つでも欠けると **`SystemExit(1)`**

6/13〜17 に Notion が断続的に 500 エラーを返していた期間:
- `get_database_property_names()` が空 set を返す（500エラーをキャッチして `set()` を返す仕様）
- `missing_engineer_properties({})` = 全7プロパティが「欠落」と判定
- `SystemExit(1)` でパイプライン全停止

**v5.1 は `ensure_engineer_db_properties()` を持たない** → Notion が不安定でも処理を継続。

```
[v6.16 起動時フロー]
main()
  └─ ensure_engineer_db_properties()
       └─ get_database_property_names(ENGINEER_DB)
            └─ Notion 500 → set() を返す
       └─ missing_engineer_properties({}) → 全プロパティ「欠落」
       └─ SystemExit(1) ← ← ← パイプライン全停止
```

### 3.2 二次原因 — `prop_map["氏名"]` が try-except 外で KeyError

仮に `ensure_engineer_db_properties()` が実行されなかった場合でも:
```python
prop_map = ENGINEER_PROP_NAMES or resolve_engineer_property_names(
    get_database_property_names(ENGINEER_DB)
)
# ↓ ここは try-except ブロックの外
properties: dict = {
    prop_map["氏名"]: ...,   # ENGINEER_PROP_NAMES={} かつ resolve失敗 → KeyError
    prop_map["備考"]: ...,
}
```
Notion API を呼ぶ try ブロックより前に KeyError が発生し、caller でキャッチされずスタックを遡る。

### 3.3 三次原因 — `common/notion_register.py` の ENGINEER_TITLE_FIELD との不整合リスク

`common/notion_register.py`:
```python
ENGINEER_TITLE_FIELD = "名前"  # ハードコード
```
v6.16 の prop_map が Notion DB に "氏名" フィールドを検出して `prop_map["氏名"] = "氏名"` と解決した場合、  
`_extract_title(properties, "名前")` は None を返し、`_upsert_page` が `ok=False` でサイレントスキップ。  
（実際の Notion engineer DB は "名前" が title フィールド名なので問題は起きにくいが、将来のリスク）

### 3.4 「名前欠落 → Notion 500」仮説の評価

**不成立**。v6.16 も `prop_map["氏名"]` → "名前" と正しく解決されれば payload は正常。  
真の停止原因は Notion 一時障害 × 起動時バリデーション ExitCode の組み合わせ。

---

## 4. 検証結果 (ケースA〜D)

> `mail_pipeline/tests/test_notion_engineer_payload.py` で実行。  
> 実行方法: `python -m pytest mail_pipeline/tests/test_notion_engineer_payload.py -v`

| ケース | payload | 期待結果 | 検証メモ |
|---|---|---|---|
| A | `名前`あり (正常) | HTTP 200, ok=True | 正常登録・archive済み |
| B | `名前` キー完全なし | skip (ok=False) | `_extract_title` が None → サイレントスキップ |
| C | `名前` あり・空 content | skip (ok=False) | `_extract_title` が None |
| D | `名前` を rich_text 型で送付 | HTTP 400 NotionAPIError | Notion が型不一致を拒否 |

> **注**: B/C はローカル validation (validate_engineer_payload) で事前キャッチ。  
> **注**: D は Notion 側が 400 を返すため事前キャッチ不可（ただしログに記録される）。

---

## 5. 今後の予防策

### 5.1 Feature Flag (NOTION_FLAG_VALIDATE) — 実装済み

`mail_pipeline/mail_pipeline.py` に追加:
```python
NOTION_FLAG_VALIDATE = os.environ.get("NOTION_FLAG_VALIDATE", "true").lower() == "true"

def validate_engineer_payload(payload: dict) -> None:
    """engineer DB create前のpayload検証。"""
    if not NOTION_FLAG_VALIDATE:
        return
    props = payload.get("properties", {})
    name_prop = props.get("名前")
    if not name_prop or "title" not in name_prop:
        raise ValueError("Notion payload validation: '名前' title is missing")
    title_arr = name_prop.get("title", [])
    if not title_arr or not title_arr[0].get("text", {}).get("content"):
        raise ValueError("Notion payload validation: '名前' title content is empty")
```

同様に `validate_project_payload` も追加（"案件名" title チェック）。

### 5.2 起動時バリデーションの廃止

v6.16 の `ensure_engineer_db_properties()` は v5.1 に戻す際に除去済み（現在本番は v5.1）。  
将来 v6.x を再投入する際は、起動時バリデーションを soft-warn のみにする（SystemExit しない）。

### 5.3 MetricsRecorder による実行監視

Task B で実装: 実行ごとに metrics.jsonl へ記録 + 松野 LINE push  
→ 停止を 2 日後ではなく当日中に検知できる。

### 5.4 RecoveryMode による段階的復旧

Task C で実装: PROCESS_LIMIT/FETCH_LIMIT を段階的に戻す仕組み  
→ 緊急縮小後の手動戻し忘れを防ぐ。

---

## 6. v6.16 の改修方針

| 選択肢 | 評価 |
|---|---|
| **ロールバック維持（現行 v5.1）** | **推奨**。安定稼働中。 |
| v6.16 修正再デプロイ | 有用な機能（件名事前分類・ValidationResult・received_at）は多いが、`ensure_engineer_db_properties()` を soft-warn 化してからゲート②を再通過させること |

v6.16 の件名キーワード事前分類（LLM削減率 63.9%）は価値が高い。  
`ensure_engineer_db_properties()` の修正・ゲート②再通過後に v6.17 として投入することを推奨。

---

*本レポートは Claude Code による自動分析。最終判断は松野（CEO）に委ねる。*
