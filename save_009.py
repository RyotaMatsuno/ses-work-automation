# -*- coding: utf-8 -*-
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PENDING = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pending_tasks"

task = """# 【Cursor作業指示】エンジニア登録時の情報取得日必須化

対象: ses_work/mail_attachment_importer/ および ses_work/matching_v3/notion_client.py
優先度: P1
根拠: 情報取得日が空欄のエンジニアがstaleness_checkerで全除外される問題（2026-06-15確認）

## 背景
- staleness_checker.py: 情報取得日が空 → is_fresh=False → filter_fresh_engineersで除外
- PHさん含む6名が情報取得日空欄でマッチングから除外されていた（ジョブズが本日一括修正済み）
- 恒久対応: エンジニア新規登録時に情報取得日を必ず埋める

## タスク1: mail_attachment_importer の Notion登録処理に情報取得日を追加

**確認対象ファイル**: ses_work/mail_attachment_importer/ 以下の Notion書き込み箇所

rg で Notion へのエンジニア登録箇所を探す:
```
rg "情報取得日" ses_work/mail_attachment_importer/
rg "pages" ses_work/mail_attachment_importer/ -l
```

登録処理の properties dict に以下を追加（既存なら確認のみ）:
```python
from datetime import datetime, timezone, timedelta
JST = timezone(timedelta(hours=9))

# propertiesに追加
"情報取得日": {"date": {"start": datetime.now(JST).strftime("%Y-%m-%d")}},
```

## タスク2: matching_v3/notion_client.py のエンジニア取得で情報取得日を含める確認

**ファイル**: ses_work/matching_v3/notion_client.py

get_active_engineers() または get_proposal_target_engineers() で取得するプロパティに
「情報取得日」が含まれているか確認する。

含まれていない場合は properties リストに追加:
```python
"情報取得日",  # staleness_checker用 必須
```

## タスク3: 情報取得日が空のエンジニアの定期チェックスクリプト追加

**新規ファイル**: ses_work/local_server/check_engineer_dates.py

```python
# -*- coding: utf-8 -*-
\"\"\"情報取得日が空のエンジニアを検出してLINE通知するスクリプト。\"\"\"
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
TOKEN = env.get("NOTION_API_KEY","")
LINE_TOKEN = env.get("LINE_CHANNEL_ACCESS_TOKEN","")
MATSUNO_ID = env.get("MATSUNO_LINE_USER_ID","")
ENG_DB = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

def npost(path, payload):
    req = urllib.request.Request(
        f"https://api.notion.com/v1/{path}",
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers=HEADERS, method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def main():
    cursor = None
    missing = []
    while True:
        payload = {"page_size": 100}
        if cursor:
            payload["start_cursor"] = cursor
        res = npost(f"databases/{ENG_DB}/query", payload)
        for page in res.get("results", []):
            props = page["properties"]
            name_p = props.get("名前",{})
            name = "".join(x.get("plain_text","") for x in name_p.get("title",[]))
            is_target = props.get("提案対象フラグ",{}).get("checkbox", False)
            date_p = props.get("情報取得日",{})
            date_val = (date_p.get("date") or {}).get("start","")
            if is_target and not date_val:
                missing.append(name or page["id"][:8])
        if not res.get("has_more"):
            break
        cursor = res.get("next_cursor")

    if missing:
        msg = f"⚠️ 情報取得日が空のエンジニア {len(missing)}名:\\n" + "\\n".join(f"・{n}" for n in missing[:10])
        req = urllib.request.Request(
            "https://api.line.me/v2/bot/message/push",
            data=json.dumps({"to": MATSUNO_ID, "messages":[{"type":"text","text":msg}]}, ensure_ascii=False).encode(),
            headers={"Authorization":f"Bearer {LINE_TOKEN}","Content-Type":"application/json"},
            method="POST"
        )
        try:
            urllib.request.urlopen(req, timeout=10)
            print(f"通知送信: {len(missing)}名")
        except Exception as e:
            print(f"通知失敗: {e}")
    else:
        print("情報取得日が空のエンジニアなし")

if __name__ == "__main__":
    main()
```

このスクリプトをタスクスケジューラに週1回（月曜8:30）で登録:
```python
import subprocess
subprocess.run([
    "schtasks", "/create", "/tn", "SES_CheckEngineerDates",
    "/tr", r'python "C:\\Users\\ma_py\\OneDrive\\デスクトップ\\ses_work\\local_server\\check_engineer_dates.py"',
    "/sc", "WEEKLY", "/d", "MON", "/st", "08:30",
    "/ru", "ma_py", "/f"
], check=True)
print("週次チェック登録完了")
```

## 完了確認
```
python local_server/check_engineer_dates.py
```
「情報取得日が空のエンジニアなし」が出ればOK。

完了後に「エンジニア日付修正完了」とClaude.aiに報告すること。
"""

path = os.path.join(PENDING, "009_engineer_date_required.md")
with open(path, "w", encoding="utf-8") as f:
    f.write(task)
print("保存: 009_engineer_date_required.md")
print(f"pending_tasks: {sorted(os.listdir(PENDING))}")
