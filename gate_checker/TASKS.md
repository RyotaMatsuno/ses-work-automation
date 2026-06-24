# TASKS.md - gate_checker v2.1 実装チェックリスト

バージョン: 2.1（Week1拡張版、GPT-5.4 条件付きGOレビュー反映）
作成日: 2026-06-16
スコープ: フェーズ別モデル + DAILY_CALL_LIMIT段階値 + 装置2 + 装置3 + 互換性対応

---

## Phase 0: ゲート①（設計レビュー）

- [ ] ゲート①再実施：SPEC.md v2.1 をレビュー → OK 取得
  - 実行モデル: 当面は `python gate_checker/spec_v2_review_by_gpt54.py` 経由で gpt-5.4
  - 既存 `gate_check.py --phase design` は GPT-4o ハルシネーション問題があるためWeek1中は使わない（別タスクで対応）

---

## Phase 1: 新規モジュール作成

- [ ] `gate_checker/phase_models.py` 新規作成
  - `PHASE_MODEL_MAP` 定数（6フェーズ × モデル × クラス）
  - `FALLBACK_MODEL = "gpt-4o"` / `FALLBACK_CLASS = "medium"`
  - `resolve_model(phase, available_models=None) -> tuple[str, str, bool]` 関数
  - .env 上書き対応:
    - `GATE_MODEL_{PHASE}` でモデル上書き
    - `GATE_MODEL_CLASS_{PHASE}` でクラス上書き（v2.1新規）
  - available_models 未マッチで fallback (gpt-4o, medium, True) を返す

- [ ] `gate_checker/cost_calc.py` 新規作成
  - `MODEL_PRICING` 単価表（5モデル分: nano/mini/5.4/codex/gpt-4o）
  - `FALLBACK_RATE = {"in": 2.50, "out": 10.00}`（gpt-4o相当）
  - `calc_actual_cost(model, in_tokens, out_tokens) -> tuple[float, bool]`
    - 未知モデルは FALLBACK_RATE で計算し fallback_used=True を返す
  - `get_cost_threshold(model_class: str) -> float`（軽=$0.025/中=$0.10/重=$0.15）

- [ ] `gate_checker/costguard_handler.py` 新規作成
  - `handle_costguard_blocked(phase, target, model, block_type, env) -> tuple[str, bool]`
    - 戻り値: (task_id, suppressed)
    - block_type: `"costguard"` または `"daily_limit"`
  - `estimate_cause(daily_usd, monthly_usd, daily_calls) -> str`
  - 重複起票防止: `results/costguard_blocks_dedup.json` で同日キー管理
    - 抑制キー: `(yyyymmdd, block_type, phase)` 複合
    - 日付が変わったら自動クリア
  - Notion AI作業キュー起票（`common.notion_register` 流用 or 直接REST）
    - task_id 形式: `gate_costguard_{block_type}_{phase}_{yyyymmdd}`
  - LINE通知（`push_or_log` 経由）
  - 失敗時の挙動: notion失敗でもLINEは試行、log に `notion_register_failed=true` 残す

---

## Phase 2: gate_check.py 改修

- [ ] `REVIEW_MODEL = "gpt-4o"` 定数を削除
- [ ] `DAILY_CALL_LIMIT = 10` → `int(os.environ.get("GATE_DAILY_CALL_LIMIT") or 30)`
- [ ] 起動時に `OpenAI.models.list()` を1回呼び、`AVAILABLE_MODELS: set[str]` を生成
  - 失敗時は空 set + WARNING ログ（API障害時も実行継続）
- [ ] `call_gpt4o()` 内部でフェーズ別モデル解決:
  - `model, model_class, fallback_used = resolve_model(phase, AVAILABLE_MODELS)`
  - OpenAI client.chat.completions.create に `model=model` を渡す
  - fallback_used=True なら WARNING + LINE通知（push_or_log、残80通閾値）
- [ ] API呼び出し**前**に `check_daily_limit()`:
  - 超過していたら API打たずに `handle_costguard_blocked(phase, target, model, "daily_limit", env)` 呼び出し
  - exit code 2
- [ ] CostGuard `can_spend()` 拒否時:
  - `handle_costguard_blocked(phase, target, model, "costguard", env)` 呼び出し
  - exit code 2
- [ ] API応答後に装置2チェック:
  - `actual_cost, cost_calc_fallback = calc_actual_cost(model, in_tokens, out_tokens)`
  - `threshold = get_cost_threshold(model_class)`
  - `actual_cost > threshold` なら `results/cost_alerts.jsonl` 追記
  - 抑制キー: `(yyyymmdd, phase, model_class)` で同日初回のみLINE通知（push_or_log、残150通閾値）
- [ ] 結果JSON に新フィールド追加:
  - `model_class` / `original_model` / `fallback_used` / `actual_cost_usd` / `cost_calc_fallback` / `cost_alert_triggered` / `cost_alert_threshold` / `daily_limit`
- [ ] TASKS.md更新時の suffix を `（{日付} GPT-4o判定:NG）` → `（{日付} {model}判定:NG）` に変更
- [ ] TASKS.md誤爆防止:
  - 既に `[!]` または `[x]` がついている行は更新しない
  - `ゲート①` を含む行が複数ある場合、最初の `[ ]` のみ更新

---

## Phase 3: .env 更新

- [ ] `config/.env` に以下を追記:
  ```
  # gate_checker v2.1
  GATE_DAILY_CALL_LIMIT=30
  # フェーズ別モデル上書き例（通常はコメントアウト）
  # GATE_MODEL_DESIGN=gpt-5.5
  # GATE_MODEL_CLASS_DESIGN=heavy
  # GATE_MODEL_IMPLEMENTATION=gpt-5.4
  ```
- [ ] 既存の `COST_GUARD_DAILY_USD=8` / `COST_GUARD_MONTHLY_USD=140` が設定済みであることを確認

---

## Phase 4: 通知優先順位の実装

- [ ] `push_or_log` 関数（既存 or 新規）が残通数を取得できる前提で:
  - 装置3: 残10通でも送信
  - NG+致命的: 残20通切ったらスキップ
  - 松野確認(OK): 残50通切ったらスキップ
  - fallback通知: 残80通切ったらスキップ
  - 装置2: 残150通切ったらスキップ
- [ ] `push_or_log` がない場合は最低限の優先度制御を costguard_handler 内に実装

---

## Phase 5: 単体テスト

- [ ] `tests/test_phase_models.py`
  - 全6フェーズで PHASE_MODEL_MAP に一致するモデルが返る
  - `GATE_MODEL_DESIGN=gpt-5.5` env で上書き
  - `GATE_MODEL_CLASS_DESIGN=heavy` env でクラス上書き
  - available_models={} で fallback (gpt-4o, medium, True) を返す
- [ ] `tests/test_cost_calc.py`
  - 既知モデル (in=1000, out=500) で期待単価と一致、fallback=False
  - 未知モデル "gpt-9.9" で gpt-4o相当レートで計算、fallback=True
- [ ] `tests/test_costguard_handler.py`
  - estimate_cause: daily=$7.5, calls=2 → "単発コスト過大..."
  - estimate_cause: calls=30, limit=30 → "回数上限到達（30/30）"
  - estimate_cause: monthly=$130 → "月次上限到達..."
  - estimate_cause: その他 → "原因不明..."
  - 重複起票防止: 同日・同block_type・同phase の2回目 → suppressed=True

---

## Phase 6: 結合テスト

- [ ] `--phase research --file dummy.md` 実行 → ログに `model=gpt-5.4-nano`
- [ ] `--phase design --file SPEC.md` 実行 → ログに `model=gpt-5.4`
- [ ] 装置2発動: cost_calc を強制超過 → `cost_alerts.jsonl` 1行 + LINEモック1回
- [ ] 装置2の同日同phase同class初回のみ:
  - 2回目はLINE通知しない
  - 異なるphaseは別カウント
  - 日付跨ぎで通知復活
  - 同phase, 異なるtargetは抑制
- [ ] 装置3発動: ledger.can_spend をmockで False → Notion dry_run + LINEモック + exit 2
- [ ] 装置3 重複起票防止: 同日2回目呼び出し → 起票・通知ともスキップ
- [ ] DAILY_CALL_LIMIT=2 で3回目 → exit 2 + 装置3起票
- [ ] モデル不在: AVAILABLE_MODELS={"gpt-4o"} で `--phase design` → fallback gpt-4o + WARN + LINEモック + 通常実行
- [ ] 未知モデルのコスト計算: ログに「fallback rate」WARN + cost_alerts.jsonl に1行（モデル名キーで日次抑制）

---

## Phase 7: exit code 2 互換性確認（v2.1 新規）

- [ ] 既存呼び出し元の棚卸し:
  - cron スクリプト
  - mail_pipeline 等の wrapper
  - CI / GitHub Actions（あれば）
  - その他 subprocess.run で gate_check.py を呼んでいる箇所
  - 検索コマンド: `rg "gate_check\.py" ses_work/ --type py`
- [ ] `returncode == 1` 前提で動いている箇所をリスト化
- [ ] 各箇所への対応方針:
  - 影響なし（returncode != 0 を一律失敗扱い）→ そのまま
  - 影響あり（exit 1 と exit 2 を区別したい）→ 対応コードを書く
- [ ] 対応箇所がある場合は別タスクとしてpending_tasks/に分離
- [ ] README.md に exit code 2 の意味を追記

---

## Phase 8: 回帰テスト

- [ ] v1.0 既存動作:
  - `--phase requirements --file SPEC.md` 動作
  - `--phase implementation --dir gate_checker` 動作
  - TASKS.md の [!] 更新動作
- [ ] agreement_checker（GPT-4o + Gemini）の動作不変
- [ ] TASKS.md 誤爆防止:
  - 既に `[!]` がついている行は更新されない
  - 既に `[x]` がついている行は更新されない

---

## Phase 9: MODEL_PRICING 検証

- [ ] OpenAI公式 pricing ページ確認: https://openai.com/api/pricing/
- [ ] gpt-5.4-nano / gpt-5.4-mini / gpt-5.4 / gpt-5.3-codex / gpt-4o の実単価を取得
- [ ] MODEL_PRICING との差異があれば修正
- [ ] SPEC.md §15 変更履歴に「YYYY-MM-DD pricing確認済」を追記
- [ ] テストの期待値を実単価で再計算

---

## Phase 10: 文書更新

- [ ] gate_checker/README.md にv2.1変更を反映（exit code 2 の意味を明記）
- [ ] SESナレッジWiki に「gate_checker v2.1 リリース」を追記

---

## Phase 11: ゲート②（コードレビュー）

- [!] ゲート②再実施：実装一式を gpt-5.4 で総合レビュー → OK 取得 （2026-06-19 GPT-4o判定:NG）
  - 当面は `--phase implementation --dir gate_checker` の代わりに、専用レビュースクリプト経由
- [ ] CostGuard稼働状況確認（cost_state.json）
- [ ] 松野へ完了報告（LINE）

---

## 完了条件

- 全Phaseチェック完了
- ゲート①・ゲート②ともに OK
- `cost_state.json` の月次累積が想定範囲内（$2.80/月 + バッファ）
- 装置2・装置3 の動作ログが `results/cost_alerts.jsonl` / `results/costguard_blocks.jsonl` に残っている
- Phase 7 で発見した呼び出し元の対応が完了している（または別タスク化）

---

## 別タスク化（Notion AI作業キュー登録予定）

- [ ] gate_checker GPT-4o ハルシネーション問題の調査・修正
  - 現象: `gate_check.py --phase design --file gate_checker/SPEC.md` 実行時、GPT-4oが実SPEC.mdの内容ではなくテンプレ的TASKS.mdをレビューしてしまう
  - 確認日: 2026-06-16
  - 影響: gate_check.py が信頼できないため、Week1中はSPEC/コードレビューを別経路（spec_v2_review_by_gpt54.py）で実施
  - 優先度: High

---

## リスク・先送り事項（Week2以降）

- [ ] DAILY_CALL_LIMIT 60→90 段階解放（2週間運用後）
- [ ] agreement_checker のフェーズ別モデル対応（命名整理含む）
- [ ] 装置1（ledger外挿検知）実装
- [ ] 装置4（自動ロールバック limit_controller.py）実装
- [ ] 二次壁打ち（high-risk全件）実装
- [ ] risk_score算出モジュール
- [ ] gate_checker専用リザーブ（CostGuard $140/月のうち専用枠）
- [ ] wall_hitting.py のCostGuard被覆確認
- [ ] Gemini単価の正確な記録（現状ledger.py default rate）
