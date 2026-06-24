ses_work/cost_guard_v2/ の SPEC_v2.10.1_patch.md と、既存の SPEC v2.10 / TASKS v2.10 / CLAUDE v2.10、および現状の実装コード(common/ledger.py、common/dedup.py、cost_guard.py)を読んで、ゲート②NG 修正(v2.10.1 patch)を実装してください。

# 前提
- v2.10 で Phase 0〜8 実装完了済み、pytest 72ケース PASS
- ゲート②(GPT-5.4 コードレビュー)で NG 判定
- 主要問題:
  1. Cursor が独自に追加した冪等性チェック(`_record_in_tx`/`_confirm_dedup_in_tx`/`_release_dedup_in_tx` の `row is None -> no-op`)がサイレントデータ破損リスク
  2. log_event() が BEGIN IMMEDIATE 未使用(SPEC §8.3 違反)
  3. stopped_budget 時の detail が空文字(SPEC §7.3.1 違反)
  4. finalize 完了状態が success/permanent しかカバーできない(transient 冪等破綻)
  5. STATE_MISMATCH ログを tx 内記録すると rollback で消える
  6. claim_id=None 経路で誤判定リスク
- 修正方針は GPT-5.4 で 3 回確認済み、「再レビューなしで実装移行可」の水準

# 読む順序(必須)
1. ses_work/cost_guard_v2/SPEC_v2.10.1_patch.md(新規、これが今回の修正仕様の真実源)
2. ses_work/cost_guard_v2/CLAUDE.md(既存ルール、変更なし)
3. ses_work/cost_guard_v2/SPEC.md(v2.10 本体、参照用)
4. ses_work/cost_guard_v2/TASKS.md(v2.10 タスクリスト、参照用)
5. 現状の実装コード(common/ledger.py、common/dedup.py、cost_guard.py)

# 改修対象ファイル
- ses_work/cost_guard.py
  - FinalizeStatus enum / FinalizeResult dataclass 追加
  - StateMismatchError 例外クラス追加(common/ledger.py に置いてもOK)
  - finalize() を SPEC_v2.10.1_patch.md §6 の完成形コードに置換
  - allowed() の stopped_budget 分岐を §7 通りに同一 tx 内読み + _log_event_in_tx 化
  - allowed() 内の他 log_event 呼び出しも _log_event_in_tx(conn, ...) に置換
- ses_work/common/ledger.py
  - _record_in_tx: 「row is None -> raise StateMismatchError」「finalized=1 -> raise StateMismatchError」に変更(§4.1)
  - _release_in_tx: 同様に厳密化(§4.3)
  - _confirm_dedup_in_tx: 同様に厳密化(§4.2)
  - _release_dedup_in_tx: DELETE → UPDATE(confirmed=1, error=2) に変更(§3.1)
  - log_event(): 公開版を BEGIN IMMEDIATE 化(§5.2)
  - _log_event_in_tx(conn, ...): 内部版を新設(§5.1)
  - _load_finalize_state_in_tx(conn, reservation_id, claim_id): 新設(§2)、FinalizeState 返却
- ses_work/common/dedup.py
  - release_dedup の SQL を DELETE → UPDATE(error=2) に変更(§3.1)
  - error 列の意味コメントを記載(§3.2: 0=success, 1=error, 2=released(transient))
- ses_work/tests/ にテスト 11本追加(SPEC_v2.10.1_patch.md §8 の表)
- 既存テストの期待値更新(SPEC_v2.10.1_patch.md §9 のリスト):
  - test_finalize_idempotent.py
  - test_finalize_atomicity.py
  - test_finalize_permanent_kinds.py
  - test_dedup_claim_transient_release.py
  - test_dedup_claim*.py(archive 条件)

# 実装方針(超重要、SPEC_v2.10.1_patch.md より)
- 「row is None」を無条件 no-op にしない(SPEC v2.10 で Cursor が独自追加した部分は廃止)
- finalize() は単一 BEGIN IMMEDIATE トランザクションで全状態判定を実行
- IDEMPOTENT/STATE_MISMATCH の判定は has_claim = decision.claim_id is not None で明示分岐
- mismatch 検出時は: 1) tx 内 rollback 2) tx 出てから別 tx で log_event 3) FinalizeResult(STATE_MISMATCH) 返却
- StateMismatchError は内部例外、外部には FinalizeResult を返す(アプリ停止しない)
- log_event 失敗時は logging.exception で記録、FinalizeResult は必ず返す(可用性優先)

# claim_id=None 経路の注意(致命点)
- has_claim = decision.claim_id is not None で明示的に分岐
- claim_id=None の場合は claim 側の状態判定をスキップ(reservation のみで idempotent/mismatch を決める)
- これがないと装置3 skip 経路で誤って STATE_MISMATCH 扱いになる

# 完了条件
- 改修対象ファイル全更新
- 新規テスト11本追加(全て PASS)
- 既存テスト期待値更新(全て PASS)
- pytest 全体で総ケース数 = 既存72 + 新規11 + 既存修正分のテストケース、全 PASS
- 完了したら、修正内容サマリ + pytest 結果を返答してください

# 行き詰まった場合
- 同じエラーで2回失敗 → ses_work/wall_hitting.py --problem "<内容>" で壁打ち
- 仕様判断不能 → Claude.ai のジョブズに質問
- begin_immediate() の context manager 実装(state_store.py)の挙動が rollback() 明示と相性悪いと感じたら、SPEC_v2.10.1_patch.md §6 の try/except 構造を「try: ... if is_mismatch: raise StateMismatchError; except StateMismatchError as e: conn.rollback(); ...」に書き換えても OK(意味は同じ)

# 注意事項
- CostGuard なしの LLM 呼び出し禁止(継続)
- 文字エンコーディング UTF-8固定
- 日本語パスを cwd/コマンドに直接渡さない
- ses_work ディレクトリ外への書き込み禁止
- 既存実装の構造を壊さず、必要な箇所のみ置換(全面書き換え不要)
