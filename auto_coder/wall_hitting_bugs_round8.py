# -*- coding: utf-8 -*-
"""Round8: Task Schedulerに依存しない恒久対策の最適解"""

import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

PROMPT = """
緊急Round8。恒久対策の最適解を決める。

# これまでの経緯まとめ
- 6/17 19:53 mail_pipeline完了 → 6/18 11:00頃まで16時間Cronスキップ(PCスリープ起因と推定)
- 6/18 11:13 唯一実行→ 17秒で謎の失敗(原因はおそらく復帰直後のネット不安定)
- 11:54 Set-ScheduledTaskでRestartCount=3追加 → 12:00 Cronスキップ(タスク更新副作用)
- 12:14 schtasks /Run → Queued滞留→子プロセス起動せず
- 12:33 /End→/Run 再投入 → cmd.exe一瞬起動して消滅
- 12:37 jobz-command経由でwd_mail_pipeline.bat直接実行 → 3分12秒で正常完走、139件処理
- 12:55 Restart-Service Schedule → OS保護で拒否
- 13:00 Cron スキップ
- 13:38 別名タスクSES_MailPipeline_R7をXMLバックアップから作成 → Ready状態
- 13:40 R7を手動Run → Queued滞留→失敗(同じパターン)
- 松野がPC再起動
- 14:21 確認: R7はReady状態(Queuedでない)、Task Schedulerサービスは131イベントで他タスク正常動作
- ただし R7 LastRun=13:40:07のまま、NextRun=15:00で14:00スキップ
- 推定: 「手動Run直後の次回Repetitionトリガをスキップ」Windows既知挙動

# 確定事実
- mail_pipeline.py本体は完璧に動く(直接実行で実証)
- A1-α(matching_v2切り離し)効いてる
- Task Schedulerは復旧したが「手動Run→次回スキップ」「Set-ScheduledTask→次回スキップ」「PCスリープ→トリガ喪失」の3重トラップ
- 一般権限ではこれらを根本解決できない

# 現状(14:25)
- 15:00 R7 Cron発火するかは観測中
- メール処理は直接実行で運用継続可能
- 緊急性は下がった、恒久対策フェーズへ

# 問い
**Q1. 恒久対策の最適解を1つ指定せよ。**
候補:
- (A) Pythonの`schedule`ライブラリで常駐スクリプト + Windows起動時自動起動
- (B) jobz-command(localhost:8765)にhourly発火機能を追加
- (C) Cloud Run + Cloud Schedulerで完全クラウド化
- (D) Task Schedulerを諦めない: タスクからRepetitionではなくCalendarTrigger×24回登録(時刻指定の重複トリガ)
- (E) WindowsサービスとしてカスタムCron Python常駐

**Q2. 選んだ案の実装規模(Cursor指示書ベース): 何時間で完成するか**

**Q3. 既存システム(matching_v3、freee、LINE bridge、AI作業キュー)との整合性: 影響範囲は**

**Q4. 副次問題: jobz-watchdog小文字版の203エラー連発はこの恒久対策で同時に解決するか、別途対応か**

**Q5. 松野に確認すべき大枠判断は何か**(費用、岡本連絡、契約変更、優先順位の観点)

**Q6. 今夜or明日中に実装して、明後日朝にはCron依存ゼロで運用したい。現実的か**

短く断定、具体的なCursor指示書方針付き。
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
header = f"=== round8 by gpt-5.4 ===\nin={usage.input_tokens} out={usage.output_tokens} cost=${cost:.4f}\n\n"
result = header + out_text
with open(
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\auto_coder\wall_hitting_bugs_round8.txt", "w", encoding="utf-8"
) as f:
    f.write(result)
print(header)
print(out_text)
