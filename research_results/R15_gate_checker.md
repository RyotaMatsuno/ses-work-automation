# R15: gate_checker 調査
調査日: 2026-06-18

## 結論（1行）
実装は v1.0 系（全フェーズ GPT-4o + Gemini 2.0 Flash 固定・日次10回）のまま残存しており、SPEC v2.2 のフェーズ別モデルルーティング・装置2・装置3は未実装；`needs_human_review()` は3層構造を持つが層3は別API呼び出しではなくレビュー本文の `HUMAN_REVIEW:` 行依存で、仕様キーワードとの乖離と層1/2の過検知リスクが残る。

## メイン処理フロー（`gate_check.py`）

```
main() → run_gate_check(phase, file, dir, tasks)
  ├─ phase 検証（6フェーズ）
  ├─ check_daily_limit()  … 超過時 save_result + return 2（装置3なし）
  ├─ パス解決 / .env 読込 / OPENAI_API_KEY 必須
  ├─ load_phase_prompt(phase)  … prompts/{phase}.txt 優先
  ├─ build_user_prompt()  … 対象ファイル/ディレクトリ + SPEC/CLAUDE/TASKS
  ├─ run_dual_review()  … agreement_checker（GPT-4o ∥ Gemini 並列）
  ├─ increment_daily_counter()  … API成功後のみ
  ├─ resolve_human_review(verdict, phase, review_text)
  ├─ verdict==OK
  │    ├─ human_review → send_line_notification（直接 LINE API）
  │    └─ save_result → return 0
  └─ verdict==NG
       ├─ human_review → send_line_notification
       ├─ else → run_wall_hitting()（subprocess）
       ├─ save_result
       ├─ update_tasks_on_ng()  … ゲート①/②フラグを [!]
       └─ return 1
```

**デッドコード**: `call_gpt4o()`（`gate_check.py:379-427`）は CostGuard 付きだが `run_gate_check` からは未呼び出し。実際の LLM 経路は `agreement_checker.run_dual_review()` のみ。

## フェーズ別モデルルーティング
| フェーズ | SPEC v2.2 設定モデル | 実装確認 |
|---|---|---|
| research | gpt-5.4-nano | **未適用** — `agreement_checker` が全フェーズ共通で `gpt-4o`（`call_gpt4o_simple`）+ `gemini-2.0-flash`（`GEMINI_URL`） |
| requirements | gpt-5.4-mini | 同上 |
| design | gpt-5.4 | 同上 |
| pre_impl | gpt-5.4 | 同上 |
| implementation | gpt-5.3-codex | 同上 |
| test | gpt-5.4-mini | 同上 |

**実装詳細**
- `phase_models.py` / `resolve_model()` は **存在しない**（`TASKS.md` Phase 1 は全項目未完了）
- `REVIEW_MODEL = "gpt-4o"` は `gate_check.py:38` に残存するが、本番経路では未使用
- 結果 JSON の `model` フィールドは常に `"gpt-4o+gemini"`（フェーズ非依存）
- `GATE_MODEL_{PHASE}` 等の .env 上書きは **未実装**
- `OpenAI.models.list()` による可用性チェック・fallback は **未実装**

## needs_human_review() 3層チェック
| 層 | 実装 | 網羅性 | リスク |
|---|---|---|---|
| 1. 完全一致キーワード | `gate_check.py:170-176` — 9語: 運用フロー, 仕様変更, データ削除, 本番DB, 契約, 岡本, コスト増, 仕様修正, 要件変更 | 調査指示・`cursor_workflow_rules.md` の例（「費用が発生」「岡本に連絡」「契約変更」）と **不一致**。「費用が発生」「契約変更」は未登録 | **FN**: 上記フレーズのみで書かれたレビューは層1をすり抜ける |
| 2. 類義語辞書 | `gate_check.py:178-211` — 7カテゴリ・計40語超（契約→取引先/請求/TERRA等、コスト増→料金増加/API料金等） | 「コスト」単体は未登録（「コスト増」カテゴリの類義のみ）。`truncate`/`drop` 等の英語語もヒット | **FP**: レビュー本文に「請求」「API料金」等が出ると層1/2で即 True（`test_human_review_override.py` で GO+HUMAN_REVIEW:NO による抑制を確認済み） |
| 3. GPT自己判定 | **別API呼び出しなし**。レビュープロンプト末尾で `HUMAN_REVIEW: YES/NO` 出力を指示（`prompts/*.txt`）し、本文に `HUMAN_REVIEW: YES` があれば True（`gate_check.py:213-214`） | `resolve_human_review()`（`gate_check.py:219-224`）で **verdict==OK かつ HUMAN_REVIEW:NO のとき層1/2を上書きして False** | **FN**: 層1/2未ヒットかつモデルが `HUMAN_REVIEW:` 行を省略、または誤って NO とした場合は人間確認なしで通過。**FN**: NG+HUMAN_REVIEW:NO は wall_hitting 経路（松野確認なし） |
| （補足） | `_phase` 引数は **未使用**（フェーズ別ルールなし） | — | research 等でプロンプトに HUMAN_REVIEW 指示がない経路は層3が機能しないが、現状は全6フェーズの `prompts/*.txt` に指示あり |

**層3プロンプト例**（`prompts/implementation.txt:14-18`）:
```
HUMAN_REVIEW: YES  ← 運用・仕様・コスト・契約・本番データに影響する場合
HUMAN_REVIEW: NO   ← 技術的な修正のみで影響範囲が実装内部に閉じる場合
判断に迷う場合は HUMAN_REVIEW: YES にしてください。
```

**組み込みプロンプト（builtin）との差**: `gate_check.py` 内の `REQUIREMENTS_SYSTEM` 等（`prompts/` 不在時のフォールバック）には `HUMAN_REVIEW` 指示が **ない**。現状は `prompts/` ファイルが存在するため通常はファイル版が使われる。

## 装置2・装置3
| 装置 | SPEC v2.2 | 実装確認 |
|---|---|---|
| **装置2** 単発コスト警告 | クラス別閾値: 軽 $0.025 / 中 $0.10 / 重 $0.15。超過時 `cost_alerts.jsonl` + LINE（同日同phase同class 1回） | **未実装** — `cost_calc.py` なし、`results/cost_alerts.jsonl` なし。`push_or_log` 未使用 |
| **装置3** CostGuard停止時 Notion 起票 | `handle_costguard_blocked()` → AI作業キュー DB（`37a450ff-...`）に `gate_costguard_{block_type}_{phase}_{yyyymmdd}`、LINE 並行、重複抑制 | **未実装** — `costguard_handler.py` なし、`costguard_blocks*.jsonl` なし |

**日次上限超過時の実際の挙動**（`gate_check.py:578-598`）:
- `DAILY_CALL_LIMIT = 10`（ハードコード。SPEC の 30 未適用）
- `verdict: LIMIT_EXCEEDED` で JSON 保存 → **return 2**
- Notion 起票なし / LINE なし / `handle_costguard_blocked` なし

**CostGuard 拒否時**（`agreement_checker.py:296-298`）:
- `can_spend(6000, 6000, "gpt-4o")` が False → `RuntimeError` → `gate_check.py` で ERROR ペイロード保存 → **return 1**（SPEC の exit 2 ではない）
- Notion 起票なし

## CostGuard自己適用
| 経路 | can_spend（事前） | record（事後） | 備考 |
|---|---|---|---|
| `agreement_checker.run_dual_review()` | **あり** — 1回のみ `can_spend(6000, 6000, "gpt-4o")` | GPT: 実トークン / Gemini: 固定 `3000/3000` | Gemini 分の事前見積もりは未個別チェック。ledger 記録モデル名 `gemini-2.5-flash` と実 API `gemini-2.0-flash` が **不一致** |
| `gate_check.call_gpt4o()` | あり（未使用デッドコード） | あり | — |
| `gate_check.send_line_notification()` | なし（LLM 不使用） | — | — |
| `run_wall_hitting()` | wall_hitting 内部で実施（本調査スコープ外だが SPEC も Week2 確認待ち） | — | NG かつ human_review=False 時に subprocess 起動 |

**ledger 上限**（`common/ledger.py`）: 日次 `COST_GUARD_DAILY_USD` デフォルト $8.0、月次 $140.0（.env 上書き可）

## エラーハンドリング
| エラー | 実装 | SPEC v2.2 との差 |
|---|---|---|
| GPT API 失敗 | `agreement_checker`: 429 は指数バックオフ最大3回。最終失敗は `ModelResult(ERROR)` → Gemini 単独 or 両方 ERROR で NG | 概ね一致 |
| Gemini API 失敗 | 429 は10秒待ち1回リトライ。ERROR 時 GPT 単独フォールバック（`judge()`） | 一致 |
| 判定パース失敗 | `parse_judgment()` → UNKNOWN/NG（保守的） | 一致 |
| CostGuard 拒否 | ERROR + exit 1 | SPEC は装置3 + exit 2 |
| 日次上限 | LIMIT_EXCEEDED + exit 2、通知・起票なし | 装置3 + exit 2 が未実装 |
| Notion API 失敗 | 該当コードなし（装置3未実装） | — |
| LINE 通知 | `send_line_notification()` が **直接** `api.line.me` に POST。429 リトライなし、失敗はログのみ | SPEC は `push_or_log` 経由（残通数確認・失敗時 Notion フォールバック）。月200通上限対応 **なし** |

## 推奨アクション
- [ ] **P0**: SPEC v2.2 Phase 1–2 を実装（`phase_models.py` / `cost_calc.py` / `costguard_handler.py` + `gate_check.py` 統合）。現状は設計のみ完了・コード未着手
- [ ] **P0**: `needs_human_review` 層1キーワードを運用仕様（「費用が発生」「岡本に連絡」「契約変更」）と同期し、「コスト」単体を類義語に追加
- [ ] **P1**: 層3の FN 対策 — `HUMAN_REVIEW:` 行が欠落した場合は保守的に True、または NG 時は常に human_review=True
- [ ] **P1**: `send_line_notification` を `line_webhook.line_bridge.push_or_log` に置換（月200通・失敗時 Notion フォールバック）
- [ ] **P1**: CostGuard 拒否時の exit code を 1→2 に変更し `handle_costguard_blocked` を接続
- [ ] **P2**: `call_gpt4o()` デッドコード削除または `run_dual_review` への CostGuard/モデルルーティング統合
- [ ] **P2**: Gemini ledger 記録モデル名（`gemini-2.5-flash`）と実 API（`gemini-2.0-flash`）の整合
- [ ] **P2**: builtin プロンプト（`REQUIREMENTS_SYSTEM` 等）にも `HUMAN_REVIEW` 指示を追加（prompts ファイル欠落時の安全網）
- [ ] **P2**: `DAILY_CALL_LIMIT` を `GATE_DAILY_CALL_LIMIT`（デフォルト30）に変更
