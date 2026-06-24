# 【Cursor作業指示】コストアラート実装（LINE通知 + 自動停止）

対象:
- ses_work/common/cost_alert.py（新規作成）
- ses_work/common/ledger.py（アラート連携を追加）
- ses_work/local_server/cron_cost_check.py（新規作成）
優先度: P0（コスト暴走防止）
根拠: 2026-06-15にmail_pipeline誤設定により$3.97/日の過剰消費が発生、Anthropicオートチャージが発動。GPT-4o・Gemini両AIが「誤設定バグが主原因・モニタリング不足が穴」と判定（2026-06-15確認）

---

## 背景

### 判明した3つの穴
1. **ledger.pyとAnthropicの実請求が別管理**: CostGuardの日次$8はledger推定値で、実際の請求が$8を超えてもオートチャージが止まらない
2. **コール数の異常を検知できない**: 今日1,800コール（平常日は200〜300コール）でも誰も気づかなかった
3. **Anthropicのプリペイド残高と月次上限設定が不明**: 残高枯渇でオートチャージが何回でも走る

### 今回修正済みの問題
- matching_v2: max_tokens 4000→8000（JSONDecodeError再試行が激減）
- mail_pipeline: 30分おき→1日3回（011タスク実装後）
- matching_v3: 2時間おき→1日1回（08:00）

---

## 実装タスク

### タスク1: cost_alert.py の新規作成

ファイル: ses_work/common/cost_alert.py

```python
# -*- coding: utf-8 -*-
"""
コストアラート管理モジュール。
ledger.pyと連携して異常コストをLINEに通知し、LLM_KILLで自動停止する。
"""
import json, os, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dotenv import dotenv_values

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = Path(__file__).resolve().parent.parent
env = dotenv_values(BASE / "config" / ".env")

JST = timezone(timedelta(hours=9))

# アラート閾値（GPT・Gemini推奨値を採用）
ALERT_THRESHOLDS = {
    "daily_warn": 6.0,     # $6/日で警告（上限$8の75%）
    "daily_kill": 8.0,     # $8/日で自動停止（LLM_KILL=1）
    "monthly_warn": 100.0, # $100/月で警告（上限$140の71%）
    "monthly_kill": 130.0, # $130/月で自動停止
    "hourly_warn": 1.5,    # $1.5/時間で警告（異常検知）
    "call_count_warn": 500, # 1時間あたりコール数500超で警告
}

ALERT_STATE_FILE = Path(os.environ.get("APPDATA","")).parent / "Local" / "ses_work_state" / "alert_state.json"
ENV_FILE = BASE / "config" / ".env"


def _load_alert_state() -> dict:
    try:
        if ALERT_STATE_FILE.exists():
            return json.loads(ALERT_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"last_alerts": {}, "kill_activated": False}


def _save_alert_state(state: dict) -> None:
    ALERT_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    ALERT_STATE_FILE.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")


def _send_line_push(message: str) -> bool:
    """松野公式LINEへプッシュ通知。"""
    import requests
    token = env.get("LINE_CHANNEL_ACCESS_TOKEN","")
    user_id = env.get("MATSUNO_LINE_USER_ID","Ue3508b43b84991f5a68281da5bf4cf39")
    if not token:
        print(f"[cost_alert] LINE未設定: {message}")
        return False
    try:
        r = requests.post(
            "https://api.line.me/v2/bot/message/push",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"to": user_id, "messages": [{"type": "text", "text": message}]},
            timeout=10
        )
        return r.status_code == 200
    except Exception as e:
        print(f"[cost_alert] LINE送信エラー: {e}")
        return False


def activate_llm_kill() -> None:
    """LLM_KILL=1をcost_state.jsonに記録し、全LLM呼び出しを停止する。"""
    try:
        state_file = Path(os.environ.get("APPDATA","")).parent / "Local" / "ses_work_state" / "cost_state.json"
        if state_file.exists():
            s = json.loads(state_file.read_text(encoding="utf-8"))
            s["llm_kill"] = True
            state_file.write_text(json.dumps(s, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"[cost_alert] LLM_KILL設定エラー: {e}")
    # 環境変数でも設定
    os.environ["LLM_KILL"] = "1"
    print("[cost_alert] LLM_KILL=1 アクティベート: 全LLM呼び出しを停止しました")


def check_and_alert(daily_usd: float, monthly_usd: float, hourly_usd: float = 0.0, hourly_calls: int = 0) -> dict:
    """
    コスト状態をチェックしてアラートを発火する。
    ledger.pyのrecord()から呼ばれる想定。
    戻り値: {"kill": bool, "alerts": [str]}
    """
    now = datetime.now(JST)
    state = _load_alert_state()
    alerts = []
    kill = False

    def already_alerted(key: str, interval_hours: int = 1) -> bool:
        """直近interval_hours時間以内に同じアラートを送信済みかチェック。"""
        last = state["last_alerts"].get(key)
        if not last:
            return False
        elapsed = (now - datetime.fromisoformat(last)).total_seconds() / 3600
        return elapsed < interval_hours

    # 日次チェック
    if daily_usd >= ALERT_THRESHOLDS["daily_kill"]:
        if not already_alerted("daily_kill"):
            msg = (
                f"🚨【緊急】LLM自動停止\n"
                f"日次コスト ${daily_usd:.2f} が上限 $8.00 に到達\n"
                f"LLM_KILL=1 で全処理を停止しました\n"
                f"明日00:00にリセットされます"
            )
            _send_line_push(msg)
            state["last_alerts"]["daily_kill"] = now.isoformat()
            activate_llm_kill()
            kill = True
            alerts.append(f"KILL: 日次${daily_usd:.2f}")

    elif daily_usd >= ALERT_THRESHOLDS["daily_warn"]:
        if not already_alerted("daily_warn", interval_hours=2):
            msg = (
                f"⚠️ コスト警告（日次）\n"
                f"本日 ${daily_usd:.2f} / 上限 $8.00（{daily_usd/8*100:.0f}%）\n"
                f"このままのペースだと上限に到達する可能性があります"
            )
            _send_line_push(msg)
            state["last_alerts"]["daily_warn"] = now.isoformat()
            alerts.append(f"WARN: 日次${daily_usd:.2f}")

    # 月次チェック
    if monthly_usd >= ALERT_THRESHOLDS["monthly_kill"]:
        if not already_alerted("monthly_kill", interval_hours=24):
            msg = (
                f"🚨【緊急】月次コスト上限に到達\n"
                f"月次コスト ${monthly_usd:.2f} が $130 に到達\n"
                f"LLM_KILL=1 で全処理を停止しました\n"
                f"月次上限 $140 まで残り ${140-monthly_usd:.2f}"
            )
            _send_line_push(msg)
            state["last_alerts"]["monthly_kill"] = now.isoformat()
            activate_llm_kill()
            kill = True
            alerts.append(f"KILL: 月次${monthly_usd:.2f}")

    elif monthly_usd >= ALERT_THRESHOLDS["monthly_warn"]:
        if not already_alerted("monthly_warn", interval_hours=24):
            msg = (
                f"⚠️ コスト警告（月次）\n"
                f"今月 ${monthly_usd:.2f} / 上限 $140（{monthly_usd/140*100:.0f}%）\n"
                f"残り ${140-monthly_usd:.2f}"
            )
            _send_line_push(msg)
            state["last_alerts"]["monthly_warn"] = now.isoformat()
            alerts.append(f"WARN: 月次${monthly_usd:.2f}")

    # 時間あたり異常検知
    if hourly_usd >= ALERT_THRESHOLDS["hourly_warn"]:
        if not already_alerted("hourly_spike", interval_hours=1):
            msg = (
                f"⚠️ コストスパイク検知\n"
                f"直近1時間のコスト ${hourly_usd:.2f}（通常の{hourly_usd/0.3:.0f}倍）\n"
                f"異常なコール数: {hourly_calls}回\n"
                f"mail_pipelineの多重実行やエラーループの可能性"
            )
            _send_line_push(msg)
            state["last_alerts"]["hourly_spike"] = now.isoformat()
            alerts.append(f"SPIKE: 時間${hourly_usd:.2f} {hourly_calls}コール")

    _save_alert_state(state)
    return {"kill": kill, "alerts": alerts}
```

### タスク2: ledger.py の record() に cost_alert 連携を追加

ses_work/common/ledger.py の record() 関数末尾に追加:

```python
# cost_alert との連携（importはtry/exceptで安全に）
try:
    from common.cost_alert import check_and_alert
    state = _load()
    check_and_alert(
        daily_usd=float(state.get("daily_usd", 0)),
        monthly_usd=float(state.get("monthly_usd", 0))
    )
except Exception:
    pass  # アラートエラーでLLM処理を止めない
```

### タスク3: cron_cost_check.py（時間あたりスパイク検知）

ファイル: ses_work/local_server/cron_cost_check.py

```python
# -*- coding: utf-8 -*-
"""
1時間あたりのコスト・コール数スパイクを検知してアラートを送る。
SES_CostCheck タスクスケジューラで毎時00分に実行。
"""
import sys, json
from pathlib import Path
from datetime import datetime, timezone, timedelta
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(__file__).resolve().parent.parent
JST = timezone(timedelta(hours=9))
cost_log = BASE / "usage_tracker" / "cost_log.jsonl"

def main():
    now = datetime.now(JST)
    one_hour_ago = now - timedelta(hours=1)
    hourly_cost = 0.0
    hourly_calls = 0

    if cost_log.exists():
        with cost_log.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    e = json.loads(line)
                    ts_str = e.get("ts","")
                    if not ts_str:
                        continue
                    ts = datetime.fromisoformat(ts_str.replace("Z","+00:00"))
                    if ts.astimezone(JST) >= one_hour_ago:
                        hourly_cost += e.get("cost_usd",0)
                        hourly_calls += 1
                except Exception:
                    pass

    # ledger正本から日次・月次取得
    state_file = Path(__file__).parent.parent.parent / "AppData" / "Local" / "ses_work_state" / "cost_state.json"
    # 実際のパス
    import os
    state_path = Path(os.environ.get("APPDATA","")).parent / "Local" / "ses_work_state" / "cost_state.json"
    daily_usd = monthly_usd = 0.0
    if state_path.exists():
        s = json.loads(state_path.read_text(encoding="utf-8"))
        daily_usd = float(s.get("daily_usd",0))
        monthly_usd = float(s.get("monthly_usd",0))

    print(f"[{now.strftime('%H:%M')}] 直近1h: ${hourly_cost:.3f} / {hourly_calls}コール | 日次: ${daily_usd:.2f} | 月次: ${monthly_usd:.2f}")

    from common.cost_alert import check_and_alert
    result = check_and_alert(daily_usd, monthly_usd, hourly_cost, hourly_calls)
    if result["alerts"]:
        print(f"アラート発火: {result['alerts']}")
    else:
        print("正常範囲")

if __name__ == "__main__":
    main()
```

タスクスケジューラ登録:
```
schtasks /create /tn SES_CostCheck /tr "python ses_work/local_server/cron_cost_check.py" /sc HOURLY /mo 1 /st 00:00 /ru ma_py /f
```

### タスク4: 動作確認

```
# アラート単体テスト（閾値を低くしてテスト）
python -c "
from common.cost_alert import check_and_alert
result = check_and_alert(daily_usd=6.5, monthly_usd=105.0, hourly_usd=0.0, hourly_calls=0)
print('alerts:', result['alerts'])
print('kill:', result['kill'])
"

# 時間別チェック単体テスト
python local_server/cron_cost_check.py
```

正常時: 「正常範囲」が出力される
異常時: LINEに通知が届く

---

## アラート閾値（GPT・Gemini両AIが推奨・ジョブズ確定）

| 種別 | 閾値 | アクション |
|---|---|---|
| 日次警告 | $6.00 | LINEに警告（2時間に1回まで） |
| 日次停止 | $8.00 | LLM_KILL=1 + LINE緊急通知 |
| 月次警告 | $100.00 | LINEに警告（1日1回まで） |
| 月次停止 | $130.00 | LLM_KILL=1 + LINE緊急通知 |
| 時間スパイク | $1.50/h | LINE警告（コール数も表示） |

---

## 完了確認

```
python local_server/cron_cost_check.py
schtasks /query /tn SES_CostCheck /fo LIST
```

完了後「コストアラート実装完了」とClaude.aiに報告すること。


## RETRY 1 REASON
exit=1 / stderr=�R�}���h ���C�����������܂��B




## RETRY 2 REASON
exit=1 / stderr=�R�}���h ���C�����������܂��B



## BLOCKED REASON
exit=1 / stderr=�R�}���h ���C�����������܂��B

