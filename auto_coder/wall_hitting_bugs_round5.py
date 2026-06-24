# -*- coding: utf-8 -*-
"""GPT-5.4 Round5 壁打ち: タスク更新→次回スキップ仮説と恒久対策"""

import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

PROMPT = """
シニア技術レビュアーとしてRound5。緊急。

# 反省と新事実
## Round4の判断ミス
Round4で「失敗時リトライ案1のみ推奨」と結論したが、これは「起動して失敗した場合」にしか効かない。
「そもそも起動しない」ケースを考慮していなかった。

## 11:54の私の作業
PowerShellでSet-ScheduledTask -InputObjectでRestartCount=3、RestartInterval=PT1Mを追加した。
Operational LogではID 140「SES_MailPipelineタスクが更新された」イベントが11:54:20に記録されている。

## 12:00 Cron結果
- 12:00ぴったりにSES_MailPipelineが起動した記録なし(Operational Logにイベントなし)
- LastRunTime: 11:13:10のまま更新されず
- NextRunTime: 13:00:00(再スケジュール済み)
- 12:14:19 手動Run発火→State=Queued(現在実行中)

## 副次発見
jobz-watchdog(小文字版)が5分ごとに203エラーで起動失敗を吐き続けている。
これがOperational Logを大量に汚している。

## 16時間スキップ(6/17 20:00〜6/18 11:00)の遠因仮説
6/17 19:53 mail_pipeline完了 → その後何らかのタスク状態変化(タスクのrun回数増加など内部状態更新)で次回がスキップされた?
あるいは、UnifiedSchedulingEngineがtrue設定でPCスリープ期間中の発火を全て切り捨てた?

# 質問
Q1. 「タスク更新後、直近の次回トリガ(11:54更新→12:00トリガ)がスキップされる」現象は実在するか?Windows Task Schedulerの既知挙動か?
Q2. もし実在するなら、今後タスクを再設定した場合の発火確実化手段は?
Q3. 16時間スキップ(6/17 20:00〜6/18 11:00)の真因として最有力なものは?
Q4. 13:00 Cronを確実に発火させるために、12:14〜12:59の間に追加で実施すべき設定変更があれば挙げよ。ただし松野(一般権限)で実行可能なものに限る。StartWhenAvailable=trueは管理者権限要否を含めて評価。
Q5. jobz-watchdog小文字版を一般権限で実質無効化する手段(Round2では「タスク変更権限がないので不可」と判定したが、`xcopy`/`del`等でターゲットファイル側を空にする方法は妥当か)。リスク評価。
Q6. 今夜中に取るべき優先度3つを示せ。

短く断定で。実行可能なPowerShellコマンド付き。
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
header = f"=== wall_hitting bugs round5 by gpt-5.4 ===\nin={usage.input_tokens} out={usage.output_tokens} cost=${cost:.4f}\n\n"
result = header + out_text
out_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\auto_coder\wall_hitting_bugs_round5.txt"
with open(out_path, "w", encoding="utf-8") as f:
    f.write(result)
print(header)
print(out_text)
