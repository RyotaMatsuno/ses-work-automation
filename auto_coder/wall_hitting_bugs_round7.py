# -*- coding: utf-8 -*-
"""Round7: Restart-Service失敗時の代替策"""

import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

PROMPT = """
緊急Round7。即断求む。

# 現状(2026-06-18 13:37時点)
- 12:14 schtasks /Run → Queued滞留(子プロセス起動せず)
- 12:33 schtasks /End → /Run 再投入 → cmd.exe一瞬起動して消滅、Queued滞留
- 12:37 jobz-command経由でwd_mail_pipeline.batを**直接実行 → 3分12秒で正常完走、139件処理成功**(matching_v2 skipped確認)
- 12:55: 松野が管理者PSで `Restart-Service -Name Schedule -Force` → **「Schedule サービスを開けません」エラー**(ScheduleはWindowsの保護サービスで通常停止不可)
- 13:00 Cron 完全スキップ
- 13:37現在: LastRun=12:33:00のままState=Queued固定
- NextRun=14:00:00

# 確定事項
- mail_pipeline.py本体は完全に健全(直接実行で実証)
- A1-α(matching_v2切り離し)は効いている
- Task Scheduler内部状態がSES_MailPipelineを「Queued」でロックしたまま
- Schedule サービスはOS保護で再起動不可

# 14:00 Cron まで残り22分

# 質問
Q1. PC再起動以外で Schedule サービス状態を回復させる手段は実在するか?
   候補:
   - (i) `schtasks /delete /tn SES_MailPipeline /f` → Queued状態ごと削除 → /Create で再作成
   - (ii) Stop-Service -Name Schedule -Force もエラー出る前提、sc.exe stop Schedule では?
   - (iii) Task Scheduler MMC (taskschd.msc) で手動操作
   - (iv) net stop Schedule
   - (v) その他

Q2. Q1-(i)タスク削除→再作成は安全か? 副作用とリスクを評価。XMLバックアップ(SES_MailPipeline_backup_20260618.xml)あり。

Q3. Task Schedulerが復旧不能な場合、代替cron実装の最適解は?
   候補:
   - (a) Pythonの`schedule`ライブラリで常駐スクリプト
   - (b) Windowsの別タスク名で新規作成
   - (c) jobz-command を hourly に叩く仕組み
   - (d) GitHub Actions の self-hosted runner
   - (e) Cloud Run + Cloud Scheduler で代替

Q4. 14:00 Cronまでの22分で取るべき最善手は? 1つ指定せよ。

Q5. ジョブズの自走範囲は? (松野は管理者PS失敗、これ以上やってもらえる作業は限定的)

短く断定、実行可能コマンド付き。
"""

resp = client.responses.create(model="gpt-5.4", reasoning={"effort": "low"}, max_output_tokens=12000, input=PROMPT)
out_text = ""
for item in resp.output:
    if item.type == "message":
        for c in item.content:
            if c.type == "output_text":
                out_text += c.text
usage = resp.usage
cost = usage.input_tokens * 1.25 / 1_000_000 + usage.output_tokens * 10 / 1_000_000
header = f"=== round7 by gpt-5.4 ===\nin={usage.input_tokens} out={usage.output_tokens} cost=${cost:.4f}\n\n"
result = header + out_text
with open(
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\auto_coder\wall_hitting_bugs_round7.txt", "w", encoding="utf-8"
) as f:
    f.write(result)
print(header)
print(out_text)
