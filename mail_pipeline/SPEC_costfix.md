# SPEC_costfix.md
# mail_pipeline コスト暴走修正 仕様書

最終更新: 2026-06-04

## 背景
mail_pipeline.py が毎回2000件超を「新規」として処理し、Anthropic API を大量コールしてコスト暴走が発生した。
本日だけで $9.30 消費し Auto-recharge($40) が発動した。

## 根本原因（確定）
1. FETCH_LIMIT=2000 / PROCESS_LIMIT=2000 → SINCEフィルタなし、毎回受信箱全件スキャン
2. save_processed_id の上限ロジックのバグ → 2000件超えで古い1000件を削除 → 削除されたIDのメールを次回また処理（無限ループ）
3. API例外発生時に save_processed_id が呼ばれない → 例外メールを毎回再処理

## 修正内容

### Fix 1: SINCE フィルタの追加（fetch_emails_from_account に実装）
- IMAPの SEARCH で "SINCE {7日前の日付}" を使い取得件数を絞る
- FETCH_LIMIT は 200 に変更（バッファとして保持）
- PROCESS_LIMIT は 50 に変更（1回の実行で最大50件処理）
- 日付フォーマット: `date(today - timedelta(days=7)).strftime("%d-%b-%Y")`
- fetch_emails_from_account 内の imap.search 呼び出しを
  `imap.search(None, 'ALL')` から
  `imap.search(None, f'SINCE {since_date}')` に変更
- 該当関数のシグネチャ: `def fetch_emails_from_account(account, limit, since_days=7)`

### Fix 2: processed_ids の上限ロジック修正
- 現状: 2000件超えたら古い1000件を削除（バグ）
- 修正後: 上限を 10000 件に引き上げ、削除は行わない
  ```python
  # [COSTFIX] 上限を10000件に引き上げ。古いIDを削除しない
  if len(ids_list) > 10000:
      ids_list = ids_list[-10000:]  # 最新10000件を保持（古い順に削除）
  ```
- ids_list[-10000:] で「最新10000件を保持」（古い方を捨てる）に変更

### Fix 3: 例外時の save_processed_id 保証
- main() のメールループ内で、各メールの処理を try/except で囲み、
  finally ブロックで必ず save_processed_id(msg_id, processed) を呼ぶ
- 対象: L1318〜L1490付近の `for i, em in enumerate(target_emails):` ループ内
- 実装イメージ:
  ```python
  for i, em in enumerate(target_emails):
      msg_id = em["msg_id"]
      try:
          # 既存の処理（subject, sender, ... classify, register, matching等）
          ...
      except Exception as ex:
          log(f"  [COSTFIX] 処理例外（スキップ）: {ex}")
      finally:
          # [COSTFIX] 例外時も必ずIDを保存して再処理を防ぐ
          save_processed_id(msg_id, processed)
  ```
- ループ内の既存の `save_processed_id(msg_id, processed)` 呼び出しはそのまま残す（重複addは無害）

### Fix 4: 日次コストガード
- mail_pipeline.py の先頭定数部分に追加:
  ```python
  # [COSTFIX] 日次API上限（ドル）
  DAILY_COST_LIMIT_USD = 2.0
  ```
- usage_tracker の cost_log.jsonl から本日の消費を読み取る関数を追加:
  ```python
  def get_today_cost_usd() -> float:
      """usage_tracker/cost_log.jsonl から今日の累計コストを返す"""
      try:
          cost_log = BASE_DIR.parent / "usage_tracker" / "cost_log.jsonl"
          if not cost_log.exists():
              return 0.0
          today = date.today().isoformat()
          total = 0.0
          with open(cost_log, encoding='utf-8') as f:
              for line in f:
                  entry = json.loads(line.strip())
                  if entry.get("date") == today:
                      total += entry.get("cost_usd", 0.0)
          return total
      except Exception:
          return 0.0
  ```
- call_claude() の先頭に以下を追加:
  ```python
  # [COSTFIX] 日次コストガード
  if get_today_cost_usd() >= DAILY_COST_LIMIT_USD:
      log(f"[COSTFIX] 日次コスト上限 ${DAILY_COST_LIMIT_USD} に達したためAPIコールをスキップ")
      return ""
  ```

## 修正対象ファイル
- `ses_work/mail_pipeline/mail_pipeline.py`

## 修正手順
1. mail_pipeline.py.bak_costfix を作成
2. Fix 1 (SINCEフィルタ + FETCH_LIMIT/PROCESS_LIMIT 変更)
3. Fix 2 (processed_ids上限修正)
4. Fix 3 (finally節でsave_processed_id保証)
5. Fix 4 (日次コストガード)
6. DRY_RUN=1 で起動確認

## 期待効果
- 1回の実行で処理するメール: 2000件 → 最大50件
- processed_ids の無限ループ消滅
- API例外後の再処理消滅
- 日次$2超えでAPI自動停止
- 月間APIコスト: 現状 ~$300/月 → 目標 $10/月以下
