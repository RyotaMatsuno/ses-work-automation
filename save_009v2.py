# -*- coding: utf-8 -*-
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PENDING = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pending_tasks"

# 既存009を削除して差し替え
for f in os.listdir(PENDING):
    if f.startswith("009"):
        os.remove(os.path.join(PENDING, f))

task = """# 【Cursor作業指示】情報取得日 自動修正デーモン（日次07:30）

対象:
- ses_work/local_server/auto_fix_engineer_dates.py（新規作成）
- ses_work/mail_attachment_importer/ 内のNotion登録処理（情報取得日の追加）
- matching_v3/notion_client.py（情報取得日の取得確認）
優先度: P1
根拠: 情報取得日空欄でマッチングから除外される問題の恒久対応（2026-06-15確認・即時分はジョブズ修正済み）

---

## タスク1: auto_fix_engineer_dates.py を新規作成

ses_work/local_server/auto_fix_engineer_dates.py:

```python
# -*- coding: utf-8 -*-
\"\"\"
情報取得日が空の提案対象エンジニアを自動で当日日付に修正する。
タスクスケジューラ SES_AutoFixEngineerDates で毎日 07:30 に実行。
08:00 の matching_v3 より前に完了させることで当日マッチングに反映する。
\"\"\"
import sys, json, urllib.request
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dotenv import dotenv_values

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = Path(r"C:\\Users\\ma_py\\OneDrive\\デスクトップ\\ses_work")
env = dotenv_values(BASE / "config" / ".env")
TOKEN = env.get("NOTION_API_KEY", "")
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}
ENG_DB = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"
JST = timezone(timedelta(hours=9))
LOG = BASE / "local_server" / "auto_fix_engineer_dates.log"


def log(msg):
    line = f"[{datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\\n")


def npost(path, payload):
    req = urllib.request.Request(
        f"https://api.notion.com/v1/{path}",
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers=HEADERS, method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def npatch(path, payload):
    req = urllib.request.Request(
        f"https://api.notion.com/v1/{path}",
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers=HEADERS, method="PATCH",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def main():
    today = datetime.now(JST).strftime("%Y-%m-%d")
    log(f"開始: 情報取得日空欄チェック (today={today})")

    cursor = None
    updated, errors = [], []

    while True:
        payload = {"page_size": 100}
        if cursor:
            payload["start_cursor"] = cursor
        res = npost(f"databases/{ENG_DB}/query", payload)

        for page in res.get("results", []):
            props = page["properties"]
            page_id = page["id"]
            # 名前取得
            name_p = props.get("名前", {})
            name = "".join(x.get("plain_text", "") for x in name_p.get("title", []))
            # 提案対象フラグ
            is_target = props.get("提案対象フラグ", {}).get("checkbox", False)
            # 情報取得日
            date_p = props.get("情報取得日", {})
            date_val = (date_p.get("date") or {}).get("start", "")

            if is_target and not date_val:
                try:
                    npatch(f"pages/{page_id}", {
                        "properties": {
                            "情報取得日": {"date": {"start": today}}
                        }
                    })
                    updated.append(name or page_id[:8])
                    log(f"  修正: {name or page_id[:8]} → {today}")
                except Exception as e:
                    errors.append(name)
                    log(f"  エラー: {name} → {e}")

        if not res.get("has_more"):
            break
        cursor = res.get("next_cursor")

    if updated:
        log(f"完了: {len(updated)}名を修正 → {updated}")
    else:
        log("完了: 修正対象なし")
    if errors:
        log(f"エラー: {errors}")


if __name__ == "__main__":
    main()
```

## タスク2: タスクスケジューラ登録

```python
import subprocess, sys
subprocess.run([
    "schtasks", "/create", "/tn", "SES_AutoFixEngineerDates",
    "/tr", f'"{sys.executable}" "C:\\\\Users\\\\ma_py\\\\OneDrive\\\\デスクトップ\\\\ses_work\\\\local_server\\\\auto_fix_engineer_dates.py"',
    "/sc", "DAILY", "/st", "07:30",
    "/ru", "ma_py", "/f"
], check=True)
print("SES_AutoFixEngineerDates 登録完了（毎日07:30）")
```

## タスク3: mail_attachment_importer の Notion登録処理に情報取得日を追加

rg で登録箇所を探す:
```
rg -n "情報取得日" ses_work/mail_attachment_importer/
rg -n "properties" ses_work/mail_attachment_importer/ -l
```

エンジニア登録の properties dict に以下を追加（未設定の場合のみ）:
```python
from datetime import datetime, timezone, timedelta
JST = timezone(timedelta(hours=9))
# properties に追加
"情報取得日": {"date": {"start": datetime.now(JST).strftime("%Y-%m-%d")}},
```

## タスク4: matching_v3/notion_client.py の取得フィールドに情報取得日が含まれているか確認

rg で確認:
```
rg -n "情報取得日" ses_work/matching_v3/notion_client.py
```

含まれていなければ get_active_engineers() または get_proposal_target_engineers() の
properties リストに追加する。

## 完了確認

```
python local_server/auto_fix_engineer_dates.py
```
→「完了: 修正対象なし」または「N名を修正」が出ること。

```
schtasks /query /tn SES_AutoFixEngineerDates /fo LIST
```
→「準備完了」が出ること。

完了後に「エンジニア日次自動修正完了」とClaude.aiに報告すること。
"""

path = os.path.join(PENDING, "009_auto_fix_engineer_dates.md")
with open(path, "w", encoding="utf-8") as f:
    f.write(task)
print("保存: 009_auto_fix_engineer_dates.md")
print(f"pending_tasks: {sorted(os.listdir(PENDING))}")
