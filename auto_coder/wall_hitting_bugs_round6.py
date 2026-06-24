# -*- coding: utf-8 -*-
"""GPT-5.4 Round6: Queued滞留時の即断"""

import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

PROMPT = """
緊急Round6。即断求む。

# 現状(2026-06-18 12:20時点)
- 11:54: Set-ScheduledTaskでRestartCount=3を追加(これが12:00スキップの原因とRound5で確定)
- 12:00: SES_MailPipeline完全スキップ(Op Logに起動イベントなし)
- 12:14:19: 私がschtasks /Run で手動発火 → Op Log ID 325(Queue入り警告) + ID 110(launch) 両方記録
- **しかし5分経過した12:19時点でpython.exeもcmd.exeも実プロセスが見当たらない**
- State=Queued 継続
- pipeline.log は11:13 FAIL以降1行も追記なし
- 過去の「Queued→3分後実行」パターン(19:48,20:09)とは違う挙動
- 13:00 Cron まで残り40分

# 副次情報
- jobz-watchdog(小文字版)が5分ごとに203エラー(0x80070002 ファイル不見つけ)を吐き続けてOp Logを汚している
- それ以外、システムリソース異常なし
- ネットワーク健全(IMAP接続0.2秒で通る)
- Python環境健全
- 私の権限は一般ユーザー(ma_py)

# 質問
Q1. このQueued滞留現象の最有力原因は?
   候補:
   - (i) Set-ScheduledTask副作用でタスクの内部状態が破損
   - (ii) Task Schedulerサービス自体の不調
   - (iii) jobz-watchdog小文字版の203連発がTask Schedulerをリソース枯渇させた可能性
   - (iv) McAfee等セキュリティソフトが子プロセス起動を阻止
   - (v) その他

Q2. 13:00 Cronまで40分。今すぐ取るべきアクションは?
   案A: 何もせず13:00観測(消極)
   案B: schtasks /End で Queued解除 → 再Run(中庸)
   案C: Task Schedulerサービス自体を再起動(net stop schedule)
   案D: 案Bを先に試して、ダメなら案C

Q3. 案Bの schtasks /End を発行した時の最悪リスクは? 副作用なしか?

Q4. もし13:00 Cron も同様に「Queued滞留→実プロセスなし」になったら、何時間も止まる可能性。どう判断する?

Q5. ジョブズが今この30分の自走判断で取る最適解1つを指定せよ。

簡潔・断定。1つの推奨と理由のみ。
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
header = f"=== wall_hitting bugs round6 by gpt-5.4 ===\nin={usage.input_tokens} out={usage.output_tokens} cost=${cost:.4f}\n\n"
result = header + out_text
out_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\auto_coder\wall_hitting_bugs_round6.txt"
with open(out_path, "w", encoding="utf-8") as f:
    f.write(result)
print(header)
print(out_text)
