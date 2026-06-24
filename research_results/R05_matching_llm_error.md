# R05: matching_v3 LLM・エラー処理調査
調査日: 2026-06-18

## 結論（1行）
本番フローで実際に動く LLM は `structurer.py` の案件メール JSON 構造化のみ（CostGuard 二重チェック済み）だが、`max_tokens=2000`・API リトライ/サーキットブレーカーなし・入力マスキングなし・フォールバック時の型検証不足が残存し、`skill_judge.py` は未配線のまま別モデル（Haiku）・別 CostGuard（v2）を持つ。

## LLM呼び出し一覧
| # | ファイル:行 | モデル | CostGuard | max_tokens | マスキング指示 |
|---|---|---|---|---|---|
| 1 | structurer.py:134 (`_call_openai`) | デフォルト `gpt-4.1-nano`（`cost_guard.get_model()` 経由。月次 $5 超で `FALLBACK_MODEL` / `gemini-2.0-flash` に降格） | **あり** — `matching_v3/cost_guard.CostGuard.can_call()` + `common.ledger.can_spend()` の二重チェック、`record_cost()` / `ledger.record()` で記録 | **2000**（8000 未満 ⚠️） | **なし** — 案件メール本文をそのまま LLM に送信。プロンプトに企業名・担当者・連絡先削除指示なし |
| 2 | structurer.py:114 (`_call_anthropic`) | 上記と同じ（非 gpt/o 系モデル選択時のフォールバック経路） | 同上 | **2000**（8000 未満 ⚠️） | 同上 |
| 3 | skill_judge.py:115 (`_do_api_call`) | デフォルト `claude-haiku-4-5-20251001`（`MATCH_MODEL` / `common/model_config.py`）— **gpt-4.1-nano ではない** | **あり** — 親ディレクトリ `ses_work/cost_guard.py` の `allowed()` / `finalize()`（v2）。`sys.path` に `ses_work` を insert して解決（`matching_v3/cost_guard.py` とは別モジュール） | **8000** ✓ | **なし** — スキル名リストのみ。固有名詞マスキング指示なし |
| — | notifier.py | LLM 呼び出しなし（テンプレート文字列で LINE 通知生成） | — | — | 部分対応 — エンジニア名はイニシャルのみ。案件名・担当者名（users.yaml キー）・生単価・粗利はそのまま表示（5 万抜き単価表記なし） |
| — | matcher.py | LLM 呼び出しなし（Python ルールベース判定） | — | — | — |

**補足（配線状況）**
- `matching_v3.py` → `structurer.structure()` のみ LLM 呼び出し。`skill_judge.judge_skills()` は **どのモジュールからも import されておらず本番未使用**。
- SPEC.md 設計思想どおり「LLM は JSON 構造化のみ」。調査指示の「メール文面生成」に相当する LLM 呼び出しは matching_v3 内に存在しない（LINE 通知は `notifier.py` の固定テンプレート）。
- **CostGuard 二重実装**: `matching_v3/cost_guard.py`（v1 クラス）と `ses_work/cost_guard.py`（v2 `allowed`/`finalize`）が同名で共存。本番 structurer は v1、skill_judge は v2 を使用。
- **SPEC.md との乖離**: SPEC §8 は `DAILY_COST_LIMIT_USD=6.00` / 月次 $120/$140 と記載するが、実装（`matching_v3/cost_guard.py`）は **$1.00/日・$5/$6 月次**（TASKS.md E2 の意図的変更）。

## エラーハンドリング評価
| 障害パターン | 処理 | 評価 |
|---|---|---|
| API タイムアウト | structurer: OpenAI/Anthropic クライアントに明示 `timeout` なし。例外は `matching_v3.py:177` で catch → case `ERROR`、リトライなし、**次案件へ継続** | **要改善** |
| API 利用上限（400 quota exceeded） | 2026-06-05 ログで **1,514 件**連続 `Structurer error`（Anthropic quota）。CostGuard は通過するため案件ごとに API を叩き続ける | **重大** — サーキットブレーカーなし |
| レート制限（429） | structurer: 処理なし。skill_judge: `RateLimitError` は `error_kind=transient` に分類するが **リトライ対象外**（529/overloaded のみ最大 5 回リトライ） | **要改善** |
| JSONDecodeError | structurer: fence 除去 → `json.loads` → 正規表現で `{...}` 抽出 → 失敗時 `extraction_confidence=0.0` の空スキーマ fallback（`structurer.py:164-214`） | **部分対応** — クラッシュは防ぐがサイレント劣化 |
| 空レスポンス | structurer: warning ログ後 fallback（`extraction_confidence=0.0`） | **部分対応** |
| max_tokens 切り詰め | structurer: `finish_reason=="length"` 時 warning のみ（`structurer.py:144-145`）。切り詰め JSON をそのまま parse 試行 | **要改善** — v2 既知バグ（8000 必要）の再発リスク |
| CostGuard 上限到達 | structurer 呼び出し前: `can_call()` false → `RuntimeError` → case `ERROR`。ループ前チェック（`matching_v3.py:167`）で **処理停止** | **良好** |
| skill_judge API 過負荷（529） | 指数バックオフ付き最大 5 回リトライ（`skill_judge.py:111-134`） | **良好**（ただし未配線） |
| レスポンス型・フィールド検証 | structurer: `isinstance(data, dict)` のみ。スキル配列の型・price 数値型チェックなし。skill_judge: `result` が ◯/×/△ 以外は × に正規化（`skill_judge.py:81-91`） | structurer **要改善** / skill_judge **良好** |

## コスト見積もり

### 1 回のマッチング実行あたり
| 処理 | LLM 呼び出し回数 | 備考 |
|---|---|---|
| 案件構造化（structurer） | **未処理案件 1 件につき 1 回** | `processed_db.is_processed()` でスキップ済み案件は 0 回 |
| エンジニアマッチング（matcher） | 0 回 | ルールベース |
| LINE 通知（notifier） | 0 回 | テンプレート |
| スキル LLM 判定（skill_judge） | 0 回（現状未配線） | 配線時は案件×スキルセットごとに 1 回の可能性 |

**典型 1 案件のトークン見積もり（structurer）**
- 入力: `len(prompt) // 4 + 200`（Few-shot 2 例 + 本文最大 3000 字）≈ 1,100〜3,500 tokens
- 出力見積もり: 300 tokens（phase0 実測 `phase0_cost_log.jsonl`: 出力 150〜452 tokens、コスト $0.00017〜0.00043/回）
- モデル `gpt-4.1-nano` 単価（`cost_guard.py`）: input $0.10/1M, output $0.40/1M
- **1 呼び出しあたり概算 $0.0002〜0.0004**

### 1 日の最大呼び出し回数
| 制限レイヤー | 上限（実装値） | 効果 |
|---|---|---|
| `matching_v3/cost_guard.py` | `DAILY_CALL_LIMIT=1500`, `DAILY_COST_LIMIT_USD=1.00` | script=matching_v3 の日次制限 |
| `common/ledger.py` | `COST_GUARD_DAILY_USD=8.0`（デフォルト） | 全 ses_work 横断の日次上限 |
| `ses_work/cost_guard.py` | `HARD_DAILY_LIMIT=20.0` | 緊急停止ライン（LLM_KILL 発動） |
| 稼働日 | 平日のみ（土日祝スキップ） | 1 日 1 回タスク想定 |
| 案件ソース | `get_new_cases(days=4)` | 4 営業日分の新規案件が対象だが processed_db で重複排除 |

**実運用上の上限**: 新規未処理案件数（通常数十件/日程度）と `DAILY_COST_LIMIT_USD=1.00` の早い方。$1 上限 ≈ 2,500〜5,000 件/日（nano 単価換算）だが、call limit 1500 が実質キャップ。**skill_judge 配線時は案件×エンジニア評価で呼び出しが爆増するため CostGuard v2 統合が必須。**

## 推奨アクション
- [ ] **P0**: `structurer.py` の `max_tokens` を OpenAI/Anthropic 両方 **8000 以上**に引き上げ（v2 JSONDecodeError 再発防止）
- [ ] **P0**: structurer に **429/529/timeout の指数バックオフリトライ**（skill_judge と同等）を追加
- [ ] **P0**: API 恒久エラー（400 quota / 401 auth）検知時に **サーキットブレーカー**でループ停止（6/5 の 1,514 連続失敗再発防止）
- [ ] **P0**: 案件メールを LLM 送信前に **企業名・担当者名・メール/電話をマスク**する前処理、またはプロンプトに削除指示を追加（守秘義務）
- [ ] **P1**: `notifier._build_msg` の単価表示を **粗利 5 万抜きの提示単価**に変更し、案件名の機密度もレビュー
- [ ] **P1**: structurer レスポンスに **スキーマバリデーション**（必須キー存在・配列型・price 数値型）を追加し、fallback 時は case を `REVIEW`/`ERROR` に明示分岐
- [ ] **P1**: `CostGuard.get_model()` の月次降格で `gemini-2.0-flash` に切り替わる経路を文書化し、`ledger.can_spend()` のモデル引数と **実際に呼ぶモデルを一致**させる
- [ ] **P2**: `skill_judge.py` を **本番配線するか削除するか**を決定。配線する場合は matcher から呼び出し、モデルを `gpt-4.1-nano` 方針に合わせるか CostGuard v2 予算を別枠設計
- [ ] **P2**: `matching_v3/cost_guard.py`（v1）と `ses_work/cost_guard.py`（v2）の **二重実装を統合**し、SPEC.md のコスト上限記載を実装値と同期
- [ ] **P2**: matching_v3 ローカル CostGuard（$1/日）と global ledger（$8/日）の **二重制限の意図**を SPEC に明記し、$50/日暴走再発時の防御深度を検証
