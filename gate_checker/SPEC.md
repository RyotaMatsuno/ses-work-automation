# SPEC.md - 自動ダブルチェックシステム（gate_checker）

バージョン: 1.0
作成日: 2026-06-09

---

## 1. 目的

開発ゲート制度（ゲート①設計レビュー / ゲート②コードレビュー）をGPT-4oで自動化し、
GO/NGをexit codeで返す。NG時はTASKS.mdのゲートフラグを `[!]` に更新する。

---

## 2. CLI仕様

```bash
python gate_checker/gate_check.py --phase <phase> --file <path> [--tasks <path>]
```

| 引数 | 必須 | 説明 |
|------|------|------|
| --phase | Yes | `requirements`（ゲート①）または `implementation`（ゲート②） |
| --file | Yes | レビュー対象ファイル（SPEC.md等）。相対パスはcwd→gate_checker/の順で解決 |
| --tasks | No | TASKS.mdパス。省略時は対象ファイルと同ディレクトリのTASKS.md |

### exit code

| code | 意味 |
|------|------|
| 0 | GO（OK / 条件付きGO） |
| 1 | NG / エラー / 日次上限超過 |

---

## 3. フェーズ定義

### 3-1. requirements（ゲート①）

- 対象: SPEC.md（＋同ディレクトリのCLAUDE.mdがあれば参照）
- チェック観点:
  - ロジックの抜け・矛盾
  - エッジケース漏れ
  - CostGuard被覆
  - 危険パラメータの無断増加リスク
  - テスト網羅性
  - 人間確認ゲートの明記
  - ロールバック可能性
- 出力フォーマット末尾: `【判定: GO】` / `【判定: 条件付きGO】` / `【判定: NG】`

### 3-2. implementation（ゲート②）

- 対象: 実装コード（.py等）＋同ディレクトリのSPEC.md
- チェック観点:
  - CostGuard被覆漏れ
  - 自動送信・本番DB書き込みの人間確認なし経路
  - SPEC制約との整合性
  - 明らかなバグ（インポートエラー・未定義変数）
  - セキュリティ（認証・署名検証）
- 出力フォーマット末尾: `【判定: GO】` / `【判定: NG】`

---

## 4. 日次上限

- gate_checker専用: **10回/日**（results/daily_counter.jsonで管理）
- 超過時: API呼び出しせず exit 1、verdict=`LIMIT_EXCEEDED`
- 日付が変わるとカウンタ自動リセット

---

## 5. CostGuard連携

- API呼び出し前: `common.ledger.can_spend()` で確認
- API呼び出し後: `common.ledger.record()` でコスト記録
- script名: `gate_checker`

---

## 6. 結果JSON

保存先: `results/gate_{phase}_{YYYYMMDD_HHMMSS}.json`

```json
{
  "timestamp": "2026-06-09T12:00:00+09:00",
  "phase": "requirements",
  "target_file": "SPEC.md",
  "tasks_file": "TASKS.md",
  "verdict": "OK",
  "judgment": "GO",
  "review_text": "...",
  "model": "gpt-4o",
  "input_tokens": 1200,
  "output_tokens": 800,
  "daily_count": 3
}
```

verdict値: `OK` / `NG` / `LIMIT_EXCEEDED` / `ERROR`

---

## 7. TASKS.md更新（NG時のみ）

- 対象: `--tasks` または対象ファイル同ディレクトリの TASKS.md
- phase=requirements → `ゲート①` を含む行の `[ ]` を `[!]` に変更
- phase=implementation → `ゲート②` を含む行の `[ ]` を `[!]` に変更
- 該当行がなければ最初の `- [ ]` を `- [!]` に変更
- 変更時に末尾へ `（{日付} GPT-4o判定:NG）` を追記

---

## 8. エラーハンドリング

| エラー | 対処 |
|--------|------|
| ファイル未存在 | ERROR出力、exit 1 |
| OPENAI_API_KEY未設定 | ERROR出力、exit 1 |
| CostGuard拒否 | ERROR出力、exit 1、verdict=ERROR |
| API 429 | exponential backoff（最大3回） |
| 判定パース失敗 | verdict=NGとして扱う |

---

## 9. 設定値（定数）

```python
DAILY_CALL_LIMIT = 10
REVIEW_MODEL = "gpt-4o"
MAX_RETRIES = 3
SCRIPT_NAME = "gate_checker"
```
