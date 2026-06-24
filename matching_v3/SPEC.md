# SPEC.md — matching_v3 仕様書

バージョン: v1.0  
作成日: 2026-06-03  
設計: ジョブズ（GPT/Gemini 壁打ち3回 + CEO承認済み）

---

## 1. システム概要

### 目的
SES 案件メールを自動処理し、適合エンジニアを Notion エンジニアDB から検索して LINE で担当者に通知する。

### 設計思想
- **LLM はJSON構造化のみ**（案件メールのテキスト → JSON）
- **マッチング判定は Python の if 文**（コスト0、透明性高い）
- バグ最小化 > コスト最安化（複雑な最適化より堅牢な単純実装）
- **ローカル JSONL を正本**（Notion はキャッシュ扱い）

### 稼働条件
- **平日（月〜金）のみ**。土日・日本の祝日は全処理スキップ（jpholiday使用）
- 1回の実行で最大 1,500 件の API 呼び出し（cost_guard.py で強制上限）

---

## 2. データフロー

```
Notion 案件DB（4営業日以内の案件）
    ↓
structurer.py：LLM (Haiku) → 案件メール本文をJSON構造化
    ↓ logs/structured.jsonl に保存（正本）
matcher.py：Notion エンジニアDB + skill_aliases.json → Python マッチング
    ↓ 判定: NG / REVIEW / MATCH
notifier.py：MATCH + REVIEW → LINE 通知
    ↓ 緊急案件=Push即時、それ以外=朝ダイジェスト
processed_db.py：全件のステータスを SQLite に記録
Notion 案件DB（業務ステータス更新）
```

---

## 3. JSON Schema v1（LLM構造化出力）

LLM はメール本文を受け取り、以下の JSON を返す。読み取れないフィールドは `null` または空配列。

```json
{
  "role": "string | null",
  "required_skills": ["string"],
  "optional_skills": ["string"],
  "ambiguous_skills": ["string"],
  "price_min": "float | null",
  "price_max": "float | null",
  "start_date": "YYYY-MM-DD | null",
  "duration_months": "int | null",
  "work_location": "string | null",
  "remote_ok": "full | partial | none | unknown",
  "interview_count": "int | null",
  "foreign_ok": "bool | null",
  "required_phases": ["string"],
  "settlement": "string | null",
  "commercial_restrictions": "string | null",
  "sole_proprietor_ok": "bool | null",
  "age_max": "int | null",
  "night_shift": "bool | null",
  "interview_scheduled_at": "ISO8601 | null",
  "extraction_confidence": "float (0.0-1.0)",
  "raw_important_notes": "string | null"
}
```

**フィールド定義:**
- `required_skills`: 必須スキル（必須・必要と明記されたもの）
- `optional_skills`: 尚可スキル
- `ambiguous_skills`: 一般的すぎる・分類困難なスキル（例: "クラウド"/"Web系"）→ REVIEW トリガー
- `price_min/max`: 単価（万円）。"〜60万" → min=null, max=60.0
- `remote_ok`: "full"=フルリモート, "partial"=週N日等, "none"=常駐, "unknown"=不明
- `extraction_confidence`: 構造化の確信度。0.7未満でREVIEW判定

---

## 4. LLM 呼び出し仕様（structurer.py）

- **モデル**: `claude-haiku-4-5-20251001`（config.py の `STRUCTURER_MODEL`、環境変数でオーバーライド可）
- **max_tokens**: 1200
- **温度**: 0（決定的出力）

### システムプロンプト

```
あなたはSES（System Engineer Staffing）案件メールからJSON情報を抽出するアシスタントです。
メール本文を読み、指定されたJSONスキーマに従って情報を抽出してください。

ルール:
- 有効なJSONのみ出力する。説明文やMarkdownコードブロックを含めない
- 読み取れないフィールドはnullまたは空配列
- required_skills: 必須・必要と明記されたスキルのみ
- optional_skills: 尚可・歓迎と明記されたスキル
- ambiguous_skills: 分類困難・一般的すぎるスキル（例: "クラウド経験"）
- price_min/max: 万円単位の数値（"〜60万"なら max=60.0, min=null）
- extraction_confidence: 抽出の確信度（不明点が多い場合は低く）
```

### Few-shot 例（`tests/fixtures.json` に2例格納）
- 例1: 通常案件（必須スキル明記・常駐・単価レンジあり）
- 例2: 面談設定済み案件（interview_scheduled_at あり）

### 入力制限（CLAUDE.md §重大ルール3との連携）
- **本文 3,000 字超**: 前 2,000 字 + 後 1,000 字に切り詰めて処理
- **本文 8,000 字超**: 処理スキップ → `processed_db` を `SKIPPED` に更新

### コスト見積もり（呼び出し前に cost_guard に渡す）
```python
est_input_tokens = len(prompt_text) // 4 + 200
est_output_tokens = 300  # 固定見積もり
```

---

## 5. スキル正規化（matcher.py 内）

`skill_aliases.json`（既存）から `SkillNormalizer` クラスを実装する。

```python
class SkillNormalizer:
    def __init__(self, aliases_path: str):
        with open(aliases_path, encoding="utf-8") as f:
            data = json.load(f)
        self.hard = {k.lower(): v for k, v in data["aliases"].items()}
        self.soft = {k.lower(): v for k, v in data["soft_aliases"].items()}
        self.soft_enabled = data.get("soft_aliases_enabled", False)

    def normalize(self, skill: str) -> str | None:
        """スキル文字列 → 31語彙の正規名称 or None（マッチ不能）"""
        key = " ".join(skill.lower().strip().split())
        if key in self.hard:
            return self.hard[key]
        if self.soft_enabled and key in self.soft:
            return self.soft[key]
        return None
```

---

## 6. マッチングアルゴリズム（matcher.py）

### 6.1 エンジニアデータ取得

**Notion DB ID**: `343450ff-37c0-819d-8769-fb0a8a4ceeb1`

取得フィールド:
| Notion プロパティ名 | 型 | 用途 |
|---|---|---|
| 名前 | title | イニシャル生成 |
| スキル | multi_select | マッチング |
| 単価（万円） | number | 単価チェック |
| 経験年数 | number | 参考情報 |
| 稼働状況 | select | アクティブフィルタ |
| 担当者 | select | 通知先判定 |
| 提案対象フラグ | checkbox | 除外判定 |
| last_edited_time | — | 鮮度チェック |
| 備考（LINEメモ） | rich_text | 並行情報抽出 |

**取得フィルタ:**
1. 提案対象フラグ = True
2. last_edited_time >= 3週間前
3. 稼働状況 in ["稼働可", "準備中", "稼働可能"] （表記ゆれに注意）

### 6.2 案件データ取得

**Notion DB ID**: `343450ff-37c0-81e4-934e-f25f90284a3c`

条件: 登録日時 >= 4営業日前（jpholiday 考慮）かつ processed_db に未登録

### 6.3 判定ロジック

```python
def judge(
    case_json: dict,
    engineer: dict,
    normalizer: SkillNormalizer
) -> tuple[str, list[str]]:
    """
    Returns: ("NG" | "REVIEW" | "MATCH", [理由リスト])
    """
    reasons: list[str] = []

    # -------- NG チェック（1つでも該当したら即 NG）--------

    # 1. 単価超過ハードフィルタ: エンジニア単価 > 案件上限 + 15万
    eng_price = float(engineer.get("単価（万円）") or 0)
    case_max = float(case_json.get("price_max") or 0)
    if case_max > 0 and eng_price > case_max + 15:
        return "NG", [f"単価超過: {eng_price}万 > 案件上限{case_max}+15万"]

    # 2. 必須スキル: 1つでも未保有なら NG
    required_raw = case_json.get("required_skills") or []
    eng_skills = set(engineer.get("スキル") or [])
    missing = []
    for s in required_raw:
        normalized = normalizer.normalize(s)
        if normalized and normalized not in eng_skills:
            missing.append(normalized)
        elif not normalized:
            # 31語彙外のスキルは REVIEW トリガーとして扱う（後述）
            reasons.append(f"語彙外スキル（要確認）: {s}")
    if missing:
        return "NG", [f"必須スキル不足: {missing}"]

    # -------- REVIEW チェック（1つでも該当したら REVIEW）--------

    # 3. 並行スコア過多
    p_score = _calc_parallel_score(engineer)
    if p_score >= 5.0:
        reasons.append(f"並行スコア過多: {p_score:.1f}")

    # 4. エンジニアデータが古い（7日超）
    last_edit = engineer.get("_last_edited_time", "")
    if last_edit and _days_since(last_edit) > 7:
        reasons.append(f"エンジニア情報古い（{_days_since(last_edit)}日前更新）")

    # 5. ambiguous_skills あり
    if case_json.get("ambiguous_skills"):
        reasons.append(f"曖昧スキルあり: {case_json['ambiguous_skills']}")

    # 6. 構造化精度低
    conf = case_json.get("extraction_confidence", 1.0)
    if conf < 0.7:
        reasons.append(f"構造化精度低: {conf:.2f}")

    if reasons:
        return "REVIEW", reasons

    # -------- MATCH --------
    return "MATCH", []


def _calc_parallel_score(engineer: dict) -> float:
    """備考（LINEメモ）フィールドからキーワードで並行スコアを推定"""
    memo = engineer.get("備考（LINEメモ）") or ""
    score = 0.0
    if "オファー中" in memo or "offer" in memo.lower():
        score += 5.0
    if "面談予定" in memo:
        score += 2.0
    if "面談調整中" in memo:
        score += 1.5
    if "結果待ち" in memo:
        score += 2.0
    return score


def _days_since(iso_str: str) -> int:
    from datetime import datetime, timezone
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - dt
        return delta.days
    except Exception:
        return 0
```

### 6.4 尚可スキルによる上振れ
- 案件 `optional_skills` の50%以上をエンジニアが保有 → 案件予算 +2万 まで許容（粗利7万目標）
- それ未満 → 案件予算内で提案（粗利5万確保）

---

## 7. 処理ステータスDB（processed_db.py）

SQLite ファイル: `matching_v3/matching_v3_processed.db`

```sql
CREATE TABLE IF NOT EXISTS processed_cases (
    case_id        TEXT PRIMARY KEY,
    email_subject  TEXT,
    email_date     TEXT,
    api_called     INTEGER DEFAULT 0,
    api_called_at  TEXT,
    business_status TEXT DEFAULT 'pending',
    -- 'pending'|'processing'|'structured'|'matched'|
    -- 'NG'|'REVIEW'|'MATCH'|'notified'|'SKIPPED'|'ERROR'
    match_results_json TEXT,
    total_cost_usd REAL DEFAULT 0.0,
    prompt_version TEXT DEFAULT 'v1',
    schema_version TEXT DEFAULT 'v1',
    created_at     TEXT DEFAULT (datetime('now', '+9 hours')),
    updated_at     TEXT DEFAULT (datetime('now', '+9 hours'))
);

CREATE TABLE IF NOT EXISTS daily_stats (
    stat_date       TEXT PRIMARY KEY,
    api_calls       INTEGER DEFAULT 0,
    total_cost_usd  REAL DEFAULT 0.0,
    ng_count        INTEGER DEFAULT 0,
    review_count    INTEGER DEFAULT 0,
    match_count     INTEGER DEFAULT 0
);
```

**ProcessedDB クラスのメソッド:**
```python
class ProcessedDB:
    def is_processed(self, case_id: str) -> bool
    def mark_api_called(self, case_id: str, subject: str, date: str) -> None
    def update_status(self, case_id: str, status: str, results: list | None = None) -> None
    def add_cost(self, case_id: str, cost_usd: float) -> None
    def get_today_stats(self) -> dict  # {"api_calls": int, "cost": float, ...}
```

---

## 8. コスト防御壁（cost_guard.py）

### 8重防御

| # | 制限 | 値 | 動作 |
|---|---|---|---|
| 1 | 1日 API 呼び出し数 | 1,500回 | 超えたら今日の処理停止 |
| 2 | 1日コスト上限 | $6.00 | 超えたら今日の処理停止 |
| 3 | 月次コスト降格閾値 | $120 | Gemini Flash-Lite へ自動切替 |
| 4 | 月次コスト停止閾値 | $140 | 全停止 + LINE 通知 |
| 5 | 呼び出し前予約チェック | 見積もり超過 | 呼ばない |
| 6 | メール本文 3,000 字超 | — | 切り詰め（前2000+後1000） |
| 7 | メール本文 8,000 字超 | — | スキップ（SKIPPED） |
| 8 | 二重起動防止 | lock file | 二重起動を防ぐ |

### CostGuard クラス仕様

```python
class CostGuard:
    DAILY_CALL_LIMIT = 1500
    DAILY_COST_LIMIT_USD = 6.00
    MONTHLY_DEGRADE_USD = 120.00
    MONTHLY_STOP_USD = 140.00
    # 既存共通ログに追記（script="matching_v3"）
    COST_LOG_PATH = "../usage_tracker/cost_log.jsonl"

    # Haiku料金: input $1/MTok, output $5/MTok
    HAIKU_INPUT_RATE = 1.0 / 1_000_000
    HAIKU_OUTPUT_RATE = 5.0 / 1_000_000

    def can_call(self, est_input_tokens: int, est_output_tokens: int) -> bool:
        """True なら呼び出し可、False なら呼び出し禁止"""

    def record_cost(self, input_tokens: int, output_tokens: int, model: str) -> None:
        """実際のトークン使用量を cost_log.jsonl に追記"""

    def get_model(self) -> str:
        """月次コストに応じてモデル名を返す（降格ロジック）"""
        monthly = self._get_monthly_cost()
        if monthly >= self.MONTHLY_DEGRADE_USD:
            return os.environ.get("FALLBACK_MODEL", "gemini-2.0-flash")
        return os.environ.get("STRUCTURER_MODEL", "claude-haiku-4-5-20251001")

    def _get_monthly_cost(self) -> float:
        """cost_log.jsonl の今月分（script="matching_v3"）を合計"""
```

---

## 9. LINE 通知（notifier.py）

### 通知モデル（ハイブリッド）

| トリガー | 方式 | 対象 |
|---|---|---|
| タイマー短い案件（3h/2h） | Push 即時 | 担当者 |
| その他 MATCH/REVIEW | 朝ダイジェスト Push（1通にまとめ） | 担当者 |
| "マッチ" コマンド | Reply API（無制限） | 送信者 |

**Push 上限**: 1日最大 8 通。超過分は翌朝ダイジェストへ。

### 通知先設定（users.yaml）

```yaml
users:
  matsuno:
    line_user_id: "Ue3508b43b84991f5a68281da5bf4cf39"
    notion_assignee: "松野"
    min_gross_profit: 5
  okamoto:
    line_user_id: "Uac1d23408573586affa37577c4e2b2ab"
    notion_assignee: "岡本"
    min_gross_profit: 3
```

### 4ケース通知ロジック

```python
def notify(case: dict, engineer: dict, verdict: str, reasons: list) -> None:
    case_user = get_user_by_notion_assignee(case.get("担当者"))
    eng_user  = get_user_by_notion_assignee(engineer.get("担当者"))

    if case_user and eng_user and case_user["key"] == eng_user["key"]:
        # 同担当 → 担当者に通知
        _enqueue(case_user, _build_msg(case, engineer, verdict, reasons))
    elif case_user and eng_user:
        # 担当者が異なる → 相互通知
        _enqueue(case_user, f"【{verdict}】{case.get('案件名', '')} - {eng_user['key']}に意向確認を依頼済み")
        _enqueue(eng_user, f"【意向確認依頼】{case.get('案件名', '')}　担当: {case_user['key']}")
```

### メッセージフォーマット

**MATCH:**
```
【MATCH】{案件名}
候補: {イニシャル} ({単価}万円)
必須スキル: 全○
案件単価: {price_min}〜{price_max}万
推定粗利: 約{gross_profit}万円
```

**REVIEW:**
```
【要確認】{案件名}
候補: {イニシャル}
確認事項:
・{reason1}
・{reason2}
```

---

## 10. エントリポイント（matching_v3.py）

```python
def main():
    # 1. 平日チェック
    if not _is_business_day():
        logger.info("非稼働日のためスキップ"); return

    # 2. 二重起動防止
    lock = LockFile(Path(__file__).parent / "matching_v3.lock")
    if not lock.acquire():
        logger.warning("別プロセスが実行中"); return

    try:
        db = ProcessedDB()
        cost_guard = CostGuard()
        notifier = Notifier()
        normalizer = SkillNormalizer("skill_aliases.json")
        notion = NotionClient()

        cases = notion.get_new_cases(days=4)  # 4営業日以内
        engineers = notion.get_active_engineers()  # 鮮度フィルタ済み

        for case in cases:
            if db.is_processed(case["id"]):
                continue

            body = case.get("人員情報原文") or ""
            if len(body) > 8000:
                db.update_status(case["id"], "SKIPPED"); continue
            if not cost_guard.can_call(len(body)//4+200, 300):
                logger.warning("コスト上限到達、処理停止"); break

            db.mark_api_called(case["id"], case.get("案件名",""), case.get("_created",""))
            try:
                case_json = structurer.structure(body, cost_guard)
            except Exception as e:
                logger.error(f"Structurer error: {e}")
                db.update_status(case["id"], "ERROR"); continue

            _save_to_jsonl("logs/structured.jsonl", case_json)
            db.update_status(case["id"], "structured")

            results = []
            for eng in engineers:
                verdict, reasons = matcher.judge(case_json, eng, normalizer)
                if verdict in ("MATCH", "REVIEW"):
                    results.append({
                        "engineer_id": eng["id"],
                        "engineer_initial": _initial(eng.get("名前","")),
                        "verdict": verdict,
                        "reasons": reasons,
                        "engineer_price": eng.get("単価（万円）"),
                    })

            db.update_status(case["id"], "matched", results)
            notion.update_match_status(case["id"], results)  # 失敗してもJSONLに残る

            for r in results:
                eng = next((e for e in engineers if e["id"] == r["engineer_id"]), {})
                notifier.enqueue(case, eng, r["verdict"], r["reasons"])

        notifier.flush()  # ダイジェスト送信

    finally:
        lock.release()
```

---

## 11. Phase 0 ドライランモード

```bash
python matching_v3.py --dry-run --input logs/phase0_emails.jsonl
```

- LINE 通知なし、Notion 書き込みなし
- 結果を `logs/phase0_results.jsonl` に書き出し
- `--input` は過去メールの JSONL ファイル（`{"id":"...","body":"..."}` 形式）

### Phase 0 合格基準（全て満たしたら Phase 1 へ）
| 指標 | 合格ライン |
|---|---|
| MATCH 適合率 | ≥ 80% |
| 取りこぼし率（本来MATCH→NG） | < 5% |
| REVIEW 率（全案件中） | < 30% |

---

## 12. Notion 連携（notion_client.py）

- API ベース: `https://api.notion.com/v1/`
- ヘッダー: `{"Authorization": "Bearer {key}", "Notion-Version": "2022-06-28"}`
- タイムアウト: 30 秒、リトライ: 3 回（指数バックオフ: 1, 2, 4 秒）

**エンジニアDBのフィルタ例:**
```json
{
  "filter": {
    "and": [
      {"property": "提案対象フラグ", "checkbox": {"equals": true}},
      {"timestamp": "last_edited_time", "last_edited_time": {"past_week": {}}}
    ]
  }
}
```

---

## 13. スケジューラ

**タスク名**: `SES_MatchingV3`  
**実行時間**: 毎朝 8:00（平日）  
**コマンド**: `python matching_v3.py`  
**作業ディレクトリ**: `ses_work/matching_v3/`  
**注意**: `SES_MatchingAndNotify`（matching_v2 用）は 2026-06-03 に無効化済み。

---

## 14. ログ出力

| ファイル | 内容 |
|---|---|
| `logs/structured.jsonl` | LLM 構造化結果（全件・正本） |
| `logs/match_results.jsonl` | マッチング結果（NG含む全件） |
| `logs/phase0_results.jsonl` | Phase0 ドライラン結果 |
| `logs/matching_v3_YYYYMMDD.log` | 実行ログ（日次ローテーション） |

**match_results.jsonl の1行フォーマット:**
```json
{
  "ts": "2026-06-03T08:05:00+09:00",
  "case_id": "notion_page_id",
  "case_name": "案件名",
  "verdict": "MATCH",
  "engineer_id": "notion_page_id",
  "engineer_initial": "T.S",
  "engineer_price": 65.0,
  "reasons": [],
  "schema_version": "v1",
  "prompt_version": "v1"
}
```

---

## 15. エッジケース処理方針（v1確定版）

| ケース | 処理方針 |
|---|---|
| `price_min`/`price_max` 両方 null | `_estimate_case_price()` で案件スキル・経験年数から推定単価を算出。推定であることを reasons に記録して REVIEW 寄せ |
| `ambiguous_skills` が空配列 | 何もしない（REVIEW トリガーなし）。null と同等に扱う |
| エンジニア単価 null | `_estimate_engineer_price()` でスキル・経験年数から推定。推定であることを reasons に記録 |
| 並行スコア >= 5.0 | 判断マニュアル v3 §5 に従い直接 NG（REVIEW ではない） |
| 処理中に例外発生 | `processed_db` に `ERROR` ステータスを記録。JSONLには残る。ロールバック手順: `processed_db` の当該 case_id を `pending` にリセットすれば再処理可能 |

### optional_skills 上振れ計算（具体的ロジック）

`matcher.optional_skill_bonus_ok()` で判定。

```python
# optional_skills のうち正規化できたもので保有率を計算
# 50% 以上保有 → 案件予算 +2万 まで許容（粗利7万目標）
# 50% 未満 → 案件予算内で提案（粗利5万確保）
```

計算例: optional_skills = [Java, AWS, Docker]、エンジニアが Java + AWS 保有 → 2/3 = 66.7% ≥ 50% → +2万許容

---

## 16. 既知の制限（v1 スコープ外）

- 並行スコアは「備考（LINEメモ）」のキーワード解析（精度に限界）→ v2 で専用フィールド化
- 地方人材フィルタは簡易実装（最寄り駅フィールドが空の場合スキップ）→ v2 で精緻化
- `required_skill_groups`（AND/OR）未実装 → v2 以降
- 1メール複数案件は未対応（最初の1案件のみ）→ v2 以降
- LINE 月 200 通上限超過時のフォールバックなし → Phase 3 で対応
