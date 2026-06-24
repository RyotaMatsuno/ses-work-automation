# 【Cursor作業指示】Task H: LINE push修正 + UTC/JST境界修正

対象ディレクトリ: ses_work/
作業内容: LINE通知バグ修正 + コスト集計の日付整合
完了条件: push判定修正 + タイムゾーン統一 + テスト
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 修正1: LINE push残通数-1時のpush試行修正（#14）

### 対象ファイル
common/line_notify.py（またはpush_or_logがある場所）

### 問題
push_or_logでremaining != 0判定のため、quota取得失敗時(-1)にpush送信してしまう。

### 修正方針
```python
# 変更前
if remaining != 0:
    push_message(...)

# 変更後
if remaining > 0:
    push_message(...)
elif remaining == -1:
    log("LINE quota取得失敗 - pushスキップしてログのみ記録")
    log_message_to_file(...)
```

### reply-onlyモード追加
```python
REPLY_ONLY_THRESHOLD = 150

def push_or_log(user_id, message):
    remaining = get_remaining_push_count()
    if remaining == -1:
        log("quota取得失敗 - ログのみ")
        log_message_to_file(message)
        return False
    if remaining <= REPLY_ONLY_THRESHOLD:
        log(f"reply-onlyモード (残{remaining}通) - ログのみ")
        log_message_to_file(message)
        return False
    if remaining > 0:
        return push_message(user_id, message)
    return False
```

### テスト
- remaining=-1: pushしない、ログ記録
- remaining=100（<150）: pushしない、ログ記録
- remaining=180（>150）: push実行
- remaining=0: pushしない

---

## 修正2: UTC/JST日付境界不整合（#20）

### 問題
cost_guardのdaily_stateはUTC基準、pipeline Layer2集計はJST基準。
UTC 00:00〜08:59（JST 09:00〜17:59）の間で日付がずれる。

### 対象ファイル
common/cost_guard.py のdaily_state読み書き

### 修正方針
cost_guard内の日付処理をJSTに統一:

```python
from datetime import timezone, timedelta

JST = timezone(timedelta(hours=9))

def _today_jst() -> str:
    from datetime import datetime
    return datetime.now(JST).strftime("%Y-%m-%d")
```

daily_stateのdate列に入れる値を _today_jst() に変更。
既存の date("now") や strftime をすべて _today_jst() に置換。

### 注意
- 既存のdaily_stateデータはUTC基準で記録されている
- 切替日に1日分のコストが分割される可能性があるが、累計には影響しない
- monthly_stateも同様にJSTに統一

### テスト
- JST 2026-06-19 08:00（UTC 2026-06-18 23:00）→ daily_stateの日付が2026-06-19
- JST 2026-06-19 00:30（UTC 2026-06-18 15:30）→ daily_stateの日付が2026-06-19

---

## 共通ルール
- 既存テスト全パス / 新規コードにtype hint
