# -*- coding: utf-8 -*-
"""Round10: 9日間ステルス故障の評価"""

import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

PROMPT = """
緊急Round10。重大発見の評価。

# 発見
ジョブズが他タスクの状態を調査中、9日間気づかれていなかったステルス故障2件を発見:

## 1. jobz_importer (mail_attachment_importer)
- Last正常実行: 2026-06-09 13:54
- それ以降ずっと255エラー(Python終了コード = bat内部のpython.exeが異常終了)
- importer.logは6/9で更新停止
- 役割: 受信メールから添付ファイル(スキルシート/契約書)を抽出してNotion/Drive登録
- 30分ごとに動作する設計

## 2. line_bridge_worker_health
- Last正常実行: 2026-06-09 13:00
- それ以降ずっと結果1(エラー終了)
- worker_health.logは6/9で更新停止  
- 役割: Cloud Run上のLINE bridge workerにhealth chをトリガー、queued/running状態を監視
- 60分ごとに動作する設計
- 注意: line bridge本体(Cloud Run)は別途5分おきにCloud Schedulerで動いてるため、これは「監視タスク」が止まってるだけ

# 業務影響仮説
- mail_attachment_importer停止: 受信メールの添付ファイル(スキルシート/契約書)が9日間ローカルNotion/Driveに取り込まれていない
- 6/9以降の添付付きメール(マッチング材料)が手付かず
- 6/15・6/16・6/17のmatching_v3はその間にも動いていた(影響あり?)
- line_bridge_worker_health停止: LINE bridge本体は別途動作中だが、health監視が止まってるためworker詰まりに気づけない

# 他の同時失敗
PC再起動後にSES_Outlook_9h/13h/18h, usage_tracker_daily, jobz_notify_weekly が「サービス利用不能(2147946720)」で同時失敗。これらは再起動直後の一時障害で次回正常化見込み(明日朝9時等)。

# 質問
Q1. mail_attachment_importer 9日停止の即時影響評価。マッチング精度に響くか?
Q2. なぜ9日前から失敗してるのか(原因仮説)? 6/9に何があったか?
Q3. 復旧の最短手順。手動でrun_importer.batを直接叩く前に確認すべきこと。
Q4. line_bridge_worker_health は急いで復旧する必要があるか? Cloud Run本体は別途動いてる前提。
Q5. ジョブズ自走範囲:
  - 失敗ログ究明 → 自走OK
  - bat手動実行 → 自走OK
  - .env/SPEC変更 → 松野確認(使い方・コスト・精度に影響する?)
  - Notion/Drive書き込み復旧 → 自走OK
Q6. PC再起動同時失敗5タスク(SES_Outlook_9h等)は静観でいいか?
Q7. 17:00 mail_pipeline scheduler発火の方が優先か、これらステルス故障対応が優先か。

短く断定、優先順位付き。
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
header = f"=== round10 by gpt-5.4 ===\nin={usage.input_tokens} out={usage.output_tokens} cost=${cost:.4f}\n\n"
result = header + out_text
with open(
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\auto_coder\wall_hitting_bugs_round10.txt", "w", encoding="utf-8"
) as f:
    f.write(result)
print(header)
print(out_text)
