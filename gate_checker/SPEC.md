# SPEC.md - 自動ダブルチェックシステム（gate_checker）

バージョン: 2.4（wall_hitting CostGuard被覆 + Sonnetタイムアウト修正）
作成日: 2026-06-09（v1.0）
更新日: 2026-07-06（v2.4）

---

## 0. バージョン履歴サマリー

| 版 | 主な変更 |
|---|---|
| 1.0 | 初版（6フェーズ対応、gpt-4o固定、DAILY_CALL_LIMIT=10） |
| 2.0 | フェーズ別モデルルーティング / DAILY_CALL_LIMIT段階値 / 装置2 / 装置3 |
| 2.1 | モデル不在fallback統一 / CostGuard定数明記 / 装置3集約キー複合化 / 未知モデルfallback計算 / exit code 2互換性タスク追加 / 通知優先順位明文化 / class override対応 / DAILY_CALL_LIMIT発火タイミング明記 |
| 2.2 | **CostGuard判定順序を統一（check_daily_limit→can_spend）** / **装置3重複時の挙動を「完全スキップ」に統一** / **§5-5の章番号誤記修正(§14→§15)** / **models.list()失敗時の明文化（空set→全phase fallback）** |
| 2.3 | **§13 通知仕様を現行コードに同期** / **agreement_checker（GPT+Sonnet）に ledger.can_spend/record 統合** / **resolve_human_review役割明記** |
| 2.4 | **wall_hitting.py CostGuard被覆完了（can_spend前 + record後・実トークン）** / **agreement_checker TIMEOUT_SECONDS 45→90・URLErrorノーリトライ追加** |

---

## 0-B. 現行実装状況（2026-07-06時点）

> **注意**: このSPECはv2.x全体の設計書です。以下は現行実装の範囲を示します。

### 実装済み（gate_check.py 現行版）
- 6フェーズ対応ゲートチェック
- GPT-4o + Claude Sonnet 4.6 合意判定（agreement_checker）
- DAILY_CALL_LIMIT チェック（`.env` GATE_DAILY_CALL_LIMIT で変更可）
- CostGuard（ledger.can_spend / record）統合
- NG時LINE通知（§13-1 仕様）
- TASKS.md ���ートフラグ更新
- 結果JSON保存（基本フィールド）
- 技術的NG時 wall_hitting.py 自動実行

### Week2以降実装予定
- §3 フェーズ別モデルルーティング（phase_models.py）→ 現在 gpt-4o 固定
- §5 装置2: 単発コスト警告（cost_calc.py）
- §6 装置3: CostGuard停止時 Notion 自動起票（costguard_handler.py）
- §8 結果JSON追加フィールド（model_class / actual_cost_usd 等）
- §13 残通数制御（push_or_log）→ 現在 send_line_notification は残通数チェックなしで送信
- exit code 2 呼び出し元互換性確認（§2）

**コードレビュー時は「Week2以降実装予定」の機能（§3フェーズ別ルーティング・§5装置2・§6装置3・§8追加JSONフィールド）が未実装であることは想定範囲内であり、NG判定の根拠としないこと。**

---

## 1. 目的

開発ゲート制度（ゲート①設計レビュー / ゲート②コードレビュー）をフェーズ別の最適モデルで自動レビューし、GO/NGをexit codeで返す。NG時はTASKS.mdのゲートフラグを `[!]` に更新する。

事故防止のためコスト・回数の三層監視（フェーズ別単発閾値 + 日次回数 + 全体ledger）を実装する。

---

## 2. CLI仕様（v1.0から不変）

```bash
python gate_checker/gate_check.py --phase <phase> --file <path> [--dir <dir>] [--tasks <path>]
```

| 引数 | 必須 | 説明 |
|------|------|------|
| --phase | Yes | `research` / `requirements` / `design` / `pre_impl` / `implementation` / `test` |
| --file | Yes（implementation除く） | レビュー対象ファイル |
| --dir | implementationのみ | レビュー対象ディレクトリ |
| --tasks | No | TASKS.mdパス |

### exit code

| code | 意味 |
|------|------|
| 0 | GO（OK / 条件付きGO） |
| 1 | NG / エラー |
| 2 | 日次上限超過 / CostGuard停止（装置3で起票済） |

**v2.x 互換性注意**:
- v1.0 では「上限超過 = exit 1」だった
- v2.x で「上限超過 = exit 2」に分離
- 既存呼び出し元（cron / バッチ / wrapper）が `returncode == 1` 前提で動いている場合は影響あり
- 対応: TASKS Phase 7 で棚卸し→必要なら呼び出し側を更新

---

## 3. フェーズ別モデルルーティング

### 3-1. デフォルトマッピング

| フェーズ | モデル | クラス | 想定月回数 | 想定月コスト |
|---|---|---|---:|---:|
| research | gpt-5.4-nano | 軽 | 5 | $0.008 |
| requirements | gpt-5.4-mini | 軽 | 15 | $0.09 |
| design | gpt-5.4 | 中 | 8 | $0.34 |
| pre_impl | gpt-5.4 | 中 | 15 | $0.30 |
| implementation | gpt-5.3-codex | 重 | 30 | $1.68 |
| test | gpt-5.4-mini | 軽 | 30 | $0.38 |

**合計想定: $2.80/月**（CostGuard月次$140に対し2%）

### 3-2. ルーティング実装

`gate_checker/phase_models.py`（新規）:

```python
PHASE_MODEL_MAP = {
    "research":       {"model": "gpt-5.4-nano", "class": "light"},
    "requirements":   {"model": "gpt-5.4-mini", "class": "light"},
    "design":         {"model": "gpt-5.4",      "class": "medium"},
    "pre_impl":       {"model": "gpt-5.4",      "class": "medium"},
    "implementation": {"model": "gpt-5.3-codex","class": "heavy"},
    "test":           {"model": "gpt-5.4-mini", "class": "light"},
}

FALLBACK_MODEL = "gpt-4o"
FALLBACK_CLASS = "medium"

def resolve_model(phase: str, available_models: set[str] | None = None) -> tuple[str, str, bool]:
    """戻り値: (model, class, fallback_used)
    available_models が None なら可用性チェックをスキップ（素通し）。
    available_models が set（空含む）の場合は、model が含まれていなければ fallback。
    .env で GATE_MODEL_{PHASE} / GATE_MODEL_CLASS_{PHASE} で上書き可。"""
    env_model_key = f"GATE_MODEL_{phase.upper()}"
    env_class_key = f"GATE_MODEL_CLASS_{phase.upper()}"
    base = PHASE_MODEL_MAP[phase]
    model = os.environ.get(env_model_key) or base["model"]
    cls = os.environ.get(env_class_key) or base["class"]
    if available_models is not None and model not in available_models:
        return FALLBACK_MODEL, FALLBACK_CLASS, True
    return model, cls, False
```

### 3-3. モデル可用性チェック（v2.2 明文化）

- 起動時に `OpenAI.models.list()` で取得した model_id set を生成
- **list_models() 失敗時**: `available_models = set()`（空 set）+ WARNING ログ
  - 全 phase が fallback gpt-4o になる（gpt-4o が空 set にも含まれないため）
  - 結果として「不在時の fallback」と同じ経路に乗る → 安全側に倒れる
  - 起動継続（API障害時も実行可能）
- `resolve_model(phase, available_models)` で fallback 判定
- fallback 発動時は WARNING ログ + LINE通知（push_or_log、月200通枠考慮）
- **エラー終了はしない**（運用継続を優先）
- 結果JSONに `fallback_used: bool` / `original_model: str` を記録
- **None と 空set の意味差**:
  - None: 可用性チェックをスキップ（テスト用、本番では使わない）
  - 空 set: 全部 fallback（list_models 失敗時の安全動作）
  - 含む set: 通常運用

### 3-4. agreement_checker との関係

- `run_dual_review()`（GPT-4o + Claude Sonnet 4.6）が合意判定ライブラリとして稼働中
- v2.2 で `call_gpt4o()` の中身を「フェーズ別モデル呼び出し」に置き換える
- 関数名は v1.0 互換のため `call_gpt4o()` のまま残す（実態と命名のズレを許容、Week2 で命名整理予定）

---

## 4. DAILY_CALL_LIMIT 段階値

### 4-1. .env で段階化

```bash
GATE_DAILY_CALL_LIMIT=30
```

- デフォルト: **30**（v1.0の10から増加）
- 段階解放: Week2安定確認後に60、さらに安定確認後90
- **90超え（110）は実装しない**（三次壁打ち結論：CostGuard比96%は危険）

### 4-2. 発火タイミング（v2.2 順序統一）

**判定順序（実装も文書もこの順番に統一）**:

1. **第1ステップ: `check_daily_limit()`**（API呼び出し前）
   - 超過していたら `handle_costguard_blocked(..., block_type="daily_limit")` → exit 2
2. **第2ステップ: `common.ledger.can_spend()`**（API呼び出し前）
   - False なら `handle_costguard_blocked(..., block_type="costguard")` → exit 2
3. **第3ステップ: API呼び出し**
4. **第4ステップ: `increment_daily_counter()` + `record()`**（API成功後）

**順序の根拠**:
- 回数チェックは内部状態のみで即時判定可能（高速・低コスト）
- ledger.can_spend は内部状態 + コスト試算が必要
- 両方発生時は `block_type="daily_limit"` を優先（先に判定するため）
- ユーザーへの説明文も「回数超過のため停止」になり、原因究明が容易

### 4-3. 30 の根拠

- 想定月回数合計: research 5 + requirements 15 + design 8 + pre_impl 15 + implementation 30 + test 30 = **103/月**
- 平均営業日 22日として 約 5/日 程度の通常運用
- バースト時（要件変更日・障害対応日）で 6倍 = 30/日 まで許容
- LINE 月200通枠への影響: 装置2/3 が同日100%発動しても、push_or_log 残通数制御で枠超過は回避

---

## 5. 装置2：フェーズ別単発コスト警告

### 5-1. 閾値

| クラス | 該当フェーズ | 単発閾値 |
|---|---|---:|
| 軽 | research / requirements / test | $0.025 |
| 中 | design / pre_impl | $0.10 |
| 重 | implementation | $0.15 |

**注**: 閾値は暫定値。Week1運用ログを元に Week2 で再校正する。

### 5-2. 発動条件

API応答後、実コスト計算結果が閾値超過したら:
1. `results/cost_alerts.jsonl` に記録
2. **同日・同phase・同クラスで最初の超過のみ** LINE通知
3. 抑制キー: `(yyyymmdd, phase, class)` 単位で1日1回
4. exit code は通常通り（GO=0 / NG=1）—警告のみで実行は止めない

### 5-3. コスト計算

`gate_checker/cost_calc.py`:

```python
MODEL_PRICING = {
    "gpt-5.4-nano":  {"in": 0.10, "out": 0.40},
    "gpt-5.4-mini":  {"in": 0.60, "out": 2.40},
    "gpt-5.4":       {"in": 2.50, "out": 10.00},
    "gpt-5.3-codex": {"in": 5.00, "out": 20.00},
    "gpt-4o":        {"in": 2.50, "out": 10.00},
}

FALLBACK_RATE = {"in": 2.50, "out": 10.00}  # gpt-4o 相当

def calc_actual_cost(model: str, in_tokens: int, out_tokens: int) -> tuple[float, bool]:
    """戻り値: (cost_usd, fallback_used)
    未知モデルは FALLBACK_RATE で計算し fallback_used=True を返す。"""
    rate = MODEL_PRICING.get(model)
    if not rate:
        rate = FALLBACK_RATE
        fallback = True
    else:
        fallback = False
    cost = in_tokens * rate["in"] / 1_000_000 + out_tokens * rate["out"] / 1_000_000
    return cost, fallback
```

未知モデル fallback 計算時:
- WARNING ログ「unknown model '{model}': cost calculated with fallback rate」
- `cost_alerts.jsonl` に `{"unknown_model": true, "model": model, ...}` を1回だけ記録（日次 + モデル名で抑制）

### 5-4. LINE通知フォーマット

```
[gate_checker 装置2] 単発コスト警告

フェーズ: {phase}
モデル: {model}{fallback_marker}
実コスト: ${cost:.4f}
閾値: ${threshold}（{class}クラス）
target: {target}

→ 通常想定の{ratio:.1f}倍。コンテキスト過大 or 異常リトライの可能性
```

`fallback_marker` は fallback=True のとき `（未知モデル fallback計算）` を付与。

### 5-5. MODEL_PRICING 検証手順

- 確認元: https://openai.com/api/pricing/
- 確認頻度: 月1回 第1月曜日、または PR で MODEL_PRICING を変更するとき
- 担当: ジョブズ → 確認後 **SPEC.md §15 変更履歴**（v2.2 章番号修正）に「YYYY-MM-DD pricing確認済」を追記
- 差異発見時: PR本文にスクショ or URLを貼って Cursor に修正依頼

---

## 6. 装置3：CostGuard停止時のNotion自動起票

### 6-1. 発動タイミング

以下のいずれかで発動:
1. `DAILY_CALL_LIMIT` 超過（→ block_type=`daily_limit`、§4-2で第1ステップ）
2. `common.ledger.can_spend()` が False を返した（→ block_type=`costguard`、§4-2で第2ステップ）

### 6-2. 重複起票防止（v2.2 完全スキップで統一）

- 抑制キー: `(yyyymmdd, block_type, phase)` の複合キー
- 同日・同block_type・同phase の起票は **2回目以降は完全スキップ**
  - **Notion起票しない / LINE通知しない / `results/costguard_blocks.jsonl` には "suppressed=true" の1行だけ追加**
  - 既存ページのcounter追記は Week2 以降（実装コスト削減のため）
- 状態管理: `results/costguard_blocks_dedup.json` で当日のキー set を保持
- 日付が変わったら自動クリア
- 戻り値: `(task_id="", suppressed=True)` を返す

### 6-3. Notion起票内容（初回のみ）

DB: AI作業キュー `37a450ff-37c0-819a-981b-c2e06ed282bb`

| プロパティ | 値 |
|---|---|
| task_id | `gate_costguard_{block_type}_{phase}_{yyyymmdd}` |
| 受付元 | gate_checker |
| 種別 | 安全装置警告 |
| 優先度 | High |
| 入力データ | phase / target / 累積コスト(daily/monthly) / 最後の実行モデル / 推定原因 / block_type |
| 担当 | jobz |
| 状態 | queued |
| 人間確認 | required |
| 作成日時 | now() |

### 6-4. CostGuard定数

```python
# config/.env で上書き可（運用値は .env を参照）
DAILY_HARD_USD = float(os.environ.get("COST_GUARD_DAILY_USD") or 8.0)
MONTHLY_USD    = float(os.environ.get("COST_GUARD_MONTHLY_USD") or 140.0)
```

- 現状の .env: `COST_GUARD_DAILY_USD=8` / `COST_GUARD_MONTHLY_USD=140`
- common/ledger.py のデフォルト値は保守的に1.0/6.0だが、運用では8.0/140.0
- `estimate_cause()` は本SPECの定数定義に従う

### 6-5. 推定原因の自動判定

```python
def estimate_cause(daily_usd: float, monthly_usd: float, daily_calls: int, block_type: str) -> str:
    # v2.2: block_type を引数に取り、原因文をブレなく決める
    if block_type == "daily_limit":
        return f"回数上限到達（{daily_calls}/{DAILY_CALL_LIMIT}）"
    if block_type == "costguard":
        if monthly_usd > MONTHLY_USD * 0.9:
            return "月次上限到達（請求書サイクル要確認）"
        if daily_usd > DAILY_HARD_USD * 0.9 and daily_calls < 5:
            return "単発コスト過大（コンテキスト肥大 or リトライ暴走の疑い）"
        if daily_usd > DAILY_HARD_USD * 0.9:
            return "日次上限到達"
        return "原因不明（cost_log.jsonl確認推奨）"
    return f"未定義block_type: {block_type}"
```

### 6-6. LINE通知

- Notion起票と並行してLINE通知（初回のみ）
- `push_or_log` 経由で月200通上限を考慮
- 重複起票防止と連動: 抑制された場合は LINE 送信もスキップ

```
[gate_checker 装置3] CostGuard停止

block_type: {block_type}
累積: daily=${daily:.3f} / monthly=${monthly:.3f}
回数: {calls}/{limit}
推定原因: {cause}

→ Notion AI作業キューに起票済（task_id: {task_id}）
詳細確認のうえ、override判断をお願いします
```

### 6-7. 実装場所

`gate_checker/costguard_handler.py`:

```python
def handle_costguard_blocked(
    phase: str,
    target: str,
    model: str,
    block_type: str,  # "costguard" | "daily_limit"
    env: dict,
) -> tuple[str, bool]:
    """CostGuard停止時の起票・通知を一括処理。
    戻り値: (task_id, suppressed)
    suppressed=True なら重複起票防止で何もしなかった（jsonl には1行残す）。"""
```

`gate_check.py` から `check_daily_limit()` 超過時 / `can_spend()` 拒否時に呼び出す。

---

## 7. CostGuard連携

判定順序は §4-2 に統一:
1. `check_daily_limit()` （API前）
2. `can_spend()` （API前）
3. API呼び出し
4. `record()` + `increment_daily_counter()` （API後）

**二層ガード構造（2026-07-06確認済み）**:

| 層 | 担当 | 実装場所 |
|---|---|---|
| 第1層（cost_guard.allowed/finalize） | agreement_checker.py の `call_gpt4o_simple` / `call_sonnet` 内 | `_cg_allowed()` / `_cg_finalize()` |
| 第2層（ledger.can_spend）| gate_check.py の `run_gate_check()` 内（API呼び出し前に両モデル分チェック → False なら exit 2） | `_ledger.can_spend()` ×2 |

`run_gate_check()` は `cost_guard.allowed()` を直接呼ばない設計（agreement_checker 内部で呼ぶため冗長を避ける）。

**wall_hitting.py**: 各LLM呼び出し成功後に実トークン（取得不能時は推定値）で `ledger.record(script="wall_hitting.py", phase="wallhit")` を呼び出す。被覆完了（2026-07-06）。

---

## 8. 結果JSON

保存先: `results/gate_{phase}_{YYYYMMDD_HHMMSS}.json`

```json
{
  "timestamp": "2026-06-16T12:00:00+09:00",
  "phase": "design",
  "target_file": "SPEC.md",
  "tasks_file": "TASKS.md",
  "verdict": "OK",
  "judgment": "GO",
  "review_text": "...",
  "model": "gpt-5.4",
  "model_class": "medium",
  "original_model": "gpt-5.4",
  "fallback_used": false,
  "input_tokens": 1200,
  "output_tokens": 800,
  "actual_cost_usd": 0.011,
  "cost_calc_fallback": false,
  "cost_alert_triggered": false,
  "cost_alert_threshold": 0.10,
  "daily_count": 3,
  "daily_limit": 30,
  "needs_human_review": false
}
```

新規フィールド（v2.x）:
- `model_class` / `actual_cost_usd` / `cost_alert_triggered` / `cost_alert_threshold` / `daily_limit`
- `original_model` / `fallback_used` / `cost_calc_fallback`

`original_model` の埋め方:
- fallback しなかった場合: 元のモデル名を入れる（model と同じ値）
- fallback した場合: 元の想定モデル（例: gpt-5.4-nano）を入れる、model には fallback 先（gpt-4o）

---

## 9. TASKS.md更新

- phase=requirements → `ゲート①` を含む行の `[ ]` を `[!]` に
- phase=implementation → `ゲート②` を含む行の `[ ]` を `[!]` に
- 末尾に `（{日付} {model}判定:NG）` を追記（実際に使ったモデル名を入れる）
- 同一行に既に `[!]` または `[x]` がついている場合は更新しない
- 該当行がない場合は最初の `- [ ]` のみを更新

---

## 10. エラーハンドリング

| エラー | 対処 |
|--------|------|
| ファイル未存在 | ERROR出力、exit 1 |
| OPENAI_API_KEY未設定 | ERROR出力、exit 1 |
| DAILY_CALL_LIMIT超過 | 装置3起票 → exit 2（第1優先） |
| CostGuard拒否 | 装置3起票 → exit 2（第2優先） |
| モデル不在（list_models未マッチ or list_models失敗） | fallback gpt-4o + WARN + LINE通知 → 通常実行 |
| API 429 | exponential backoff（最大3回） |
| 判定パース失敗 | verdict=NGとして扱う |
| 装置3 Notion起票失敗 | LINE通知は実行、`costguard_blocks.jsonl` に `notion_register_failed=true` を残す |
| `--file` と `--dir` 両方未指定（implementation） | ERROR出力、exit 1 |
| `--dir` 指定だが implementation 以外 | ERROR出力、exit 1 |

---

## 11. 設定値（統合）

```python
# .env で上書き可
DAILY_CALL_LIMIT = int(os.environ.get("GATE_DAILY_CALL_LIMIT") or 30)
DAILY_HARD_USD   = float(os.environ.get("COST_GUARD_DAILY_USD") or 8.0)
MONTHLY_USD      = float(os.environ.get("COST_GUARD_MONTHLY_USD") or 140.0)

# 装置2閾値
COST_ALERT_THRESHOLDS = {
    "light":  0.025,
    "medium": 0.10,
    "heavy":  0.15,
}

# Fallback
FALLBACK_MODEL = "gpt-4o"
FALLBACK_CLASS = "medium"
FALLBACK_RATE = {"in": 2.50, "out": 10.00}

# その他
MAX_RETRIES = 3
SCRIPT_NAME = "gate_check.py"  # ledger.record に使用（§7）
```

---

## 12. テスト方針

### 単体テスト
- `phase_models.resolve_model()`:
  - 全6フェーズでデフォルトマッピング通り返る
  - `GATE_MODEL_DESIGN=gpt-5.5` env で上書き
  - `GATE_MODEL_CLASS_DESIGN=heavy` env で class上書き
  - available_models=None で素通し
  - available_models=set() で全 phase fallback
  - available_models={"gpt-4o"} 等で 主要モデルは fallback、gpt-4o はそのまま
- `cost_calc.calc_actual_cost()`:
  - 既知モデル: 期待値と一致、fallback=False
  - 未知モデル: gpt-4o 相当のレートで計算、fallback=True
- `costguard_handler.estimate_cause()`:
  - block_type="daily_limit", calls=30, limit=30 → "回数上限到達（30/30）"
  - block_type="costguard", monthly=$130 → "月次上限到達..."
  - block_type="costguard", daily=$7.5, calls=2 → "単発コスト過大..."
  - block_type="costguard", daily=$7.5, calls=10 → "日次上限到達"
  - block_type="未定義" → "未定義block_type: ..."
- `costguard_handler` 重複起票防止:
  - 同日・同block_type・同phase の2回目呼び出し → suppressed=True（Notion・LINE共にスキップ、jsonl 1行）

### 結合テスト
- `--phase research --file dummy.md` 実行 → ログに `model=gpt-5.4-nano`
- `--phase design --file SPEC.md` 実行 → ログに `model=gpt-5.4`
- 装置2発動: cost_calc を強制超過 → `cost_alerts.jsonl` 1行追加 + LINEモック1回
- 装置2の同日同phase同class初回のみ:
  - 2回目はLINE通知しない
  - 異なるphaseは別カウント
  - 日付跨ぎで通知復活
  - 同phase, 異なるtargetは抑制
- 装置3発動: ledger.can_spend をmockで False → Notion dry_run + LINEモック + exit 2
- 装置3 重複起票防止: 同日2回目呼び出し → 起票・通知ともスキップ、jsonl 1行
- DAILY_CALL_LIMIT=2 で3回目 → block_type="daily_limit" で装置3起票 + exit 2
- DAILY_CALL_LIMIT超過と CostGuard拒否 同時発生 → daily_limit が先（第1優先）に発動
- モデル不在: AVAILABLE_MODELS={"gpt-4o"} で `--phase design` → fallback gpt-4o + WARN + LINEモック + 通常実行
- list_models() 失敗（空 set）: 全 phase が fallback gpt-4o（LINE通知は phase ごとに1回、ただしモデル名キーで日次1回に集約）
- 未知モデルのコスト計算: ログに「fallback rate」WARN + cost_alerts.jsonl に1行（モデル名キーで日次抑制）

### 回帰テスト
- v1.0 既存動作:
  - `--phase requirements --file SPEC.md` 動作
  - `--phase implementation --dir gate_checker` 動作
  - TASKS.md の [!] 更新動作
- agreement_checker（GPT-4o + Claude Sonnet 4.6）の動作不変

### TASKS.md 誤爆防止テスト
- 既に `[!]` がついている行は更新されない
- 既に `[x]` がついている行は更新されない
- `ゲート①` を含む行が複数ある場合、最初の `[ ]` のみ更新
- 該当キーワードがない場合のフォールバック動作

### exit code 2 互換性テスト
- `subprocess.run(...).returncode == 2` を受ける wrapper を1個用意し、想定通り動くか確認
- v1.0 想定の `returncode == 1` ハンドラがある場合の挙動確認

### 通知優先順位テスト
- push_or_log の残通数閾値ごとの境界（残149/150/151通など）
- 残10通でも装置3は送信される

---

## 13. 通知優先順位

LINE月200通枠を守るため、抑制順位:

| 優先度 | 通知種別 | 抑制 | 残通数閾値 |
|---:|---|---|---:|
| 1 | 装置3（CostGuard停止） | 重複起票防止のみ、原則送信 | 残10通でも送る |
| 2 | NG（全件）1行通知・返信要求なし | 同一target+phase で1日1回 | 残20通切ったらスキップ |
| 3 | **廃止** ~~松野確認要（OK時）~~ | - | - |
| 4 | モデル不在fallback発動 | 1日1回（モデル名キー、phase 跨いで1回に集約） | 残80通切ったらスキップ |
| 5 | 装置2（単発コスト警告） | 同日同phase同class で1日1回 | 残150通切ったらスキップ |

`push_or_log` で残通数を取得し、上記閾値で判定する。

### 13-1. 現行通知仕様（v2.3同期）

- **verdict=OK**: LINE通知なし。ログ出力 + results JSON への記録のみ。
- **verdict=NG**: 1行通知（`[gate] {phase} NG: {filename} → ジョブズ対応中・返信不要`）。返信要求なし。
- **松野判断の提起**: ジョブズが Claude.ai チャネルで行う。コードは関与しない。
- **`resolve_human_review()` の役割**: NG内容の分類（仕様的/技術的）を `needs_human_review` フィールドとして results JSON に記録するのみ。LINE通知の有無には影響しない（NG全件通知・OK全件無通知で統一）。

**Week2課題**: 同一実行内で複数通知（fallback + 装置2が同時発生）が起きた場合の集約は v2.x スコープ外。Week2 で「実行ID単位で1通に統合」を検討。

---

## 14. リスクと未確定事項

| 項目 | リスク | 対応 |
|---|---|---|
| MODEL_PRICING単価 | 2026-06時点の推定値 | 月1回 第1月曜日に OpenAI公式と照合（§5-5） |
| gpt-5.4-nano/codex の正式名 | 公式と異なる可能性 | 起動時に list_models() で検証、不在なら fallback gpt-4o |
| Notion API レート制限 | 装置3で連発起票するとhit | 複合キー (date+block_type+phase) で同日完全スキップ |
| LINE 月200通上限 | 装置2+3で通知過多になる可能性 | §13 通知優先順位＋残通数別閾値 |
| agreement_checker | GPT-4o + Claude Sonnet 4.6 で稼働。フェーズ別モデルとは別系統 | v2.x スコープ外、Week2 で統一検討 |
| wall_hitting.py | ~~CostGuard被覆が未検証~~ | 2026-07-06 被覆完了（can_spend前 + record後） |
| exit code 2 既存呼び出し側 | 旧 returncode==1 前提で動く可能性 | TASKS Phase 7 で棚卸し |
| OpenAI.models.list() 失敗 | 全 phase fallback でLINE通知集中 | モデル名キーで日次1回に集約（§13） |
| gate_check.py 自身のハルシネーション | 既知バグあり（2026-06-16確認） | Week1 中はSPEC/コードレビューを別経路（spec_v2_review_by_gpt54.py）で実施、別タスク化済 |

---

## 15. 変更履歴

| 日付 | 版 | 変更 |
|---|---|---|
| 2026-06-09 | 1.0 | 初版（6フェーズ対応、gpt-4o固定、DAILY_CALL_LIMIT=10） |
| 2026-06-16 | 2.0 | フェーズ別モデルルーティング / DAILY_CALL_LIMIT段階値 / 装置2 / 装置3 |
| 2026-06-16 | 2.1 | モデル不在fallback統一 / CostGuard定数明記 / 装置3集約キー複合化 / 未知モデルfallback計算 / exit code 2互換性タスク追加 / 通知優先順位明文化 / class override対応 / DAILY_CALL_LIMIT発火タイミング明記 |
| 2026-06-16 | 2.2 | CostGuard判定順序統一（daily_limit→costguard）/ 装置3重複時を「完全スキップ」に統一 / §5-5の章番号誤記修正（§14→§15）/ models.list()失敗時を空set→全phase fallback と明文化 / estimate_cause()に block_type 引数追加 / original_model 埋め方仕様明記 / Week2課題（同一実行内通知集約）追加 |
| 2026-07-06 | 2.3 | §13 通知仕様を現行コードに同期: OK時=通知なし（ログ+results JSON）/ NG時=1行・返信不要 / resolve_human_review役割明記（results JSON記録のみ）/ gate_check.py に ledger.can_spend/record 統合（exit code 2対応） |
| 2026-07-06 | 2.4 | wall_hitting.py CostGuard被覆完了（§7更新）/ agreement_checker TIMEOUT_SECONDS 45→90・URLErrorノーリトライ追加 |
