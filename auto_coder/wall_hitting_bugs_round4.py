# -*- coding: utf-8 -*-
"""
GPT-5.4 Round4 壁打ち
新規発見問題:
- 6/17 19:53完了後、16時間Cronスキップ(20:00,21:00,...,10:00)
- 6/18 11:13に唯一実行されたが17秒で原因不明の失敗
- import/syntax/-Pオプションは全て健全
- 標準エラーもpipeline.logにリダイレクトされているが11:13:26 START〜11:13:44 FAILの間にログ1行も書かれていない
"""

import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

PROMPT = """
あなたはSES営業基盤のシニア技術レビュアー。Round3続きのRound4です。

# 新規発見問題(2026-06-18 11:25時点)

## 問題1: 16時間Cronスキップ
- 6/17 19:53:00 mail_pipeline正常完了
- 6/17 20:00〜23:00 と 6/18 0:00〜10:00 のCronがすべてスキップ
- pipeline.logにはこの16時間まったく実行ログなし
- 6/18 11:13:26 にようやく実行(11:00ぴったりでもない)
- Round3で「Operational Log有効化」をCEOに依頼中。原因究明は次回スキップで取れる予定

## 問題2: 11:13実行の17秒突然死
- 11:13:26.85 [===== mail_pipeline START =====]
- 11:13:44.94 [mail_pipeline FAIL] (run_pipeline.batのERRORLEVEL検知echo)
- **この間18秒、pipeline.logに1行も出力なし(stderrも >> でlogに行く設定)**
- python -V: 3.12.10 OK
- python -P オプション: 動作OK
- mail_pipeline.py syntax check: OK
- skill_reader/skill_reader と usage_tracker/cost_logger のimport: OK
- LLM_KILL環境変数: 未設定
- cost_state.json: AppData/Localやproject直下に見つからず
- mail_pipeline.pyは冒頭で sys.stdout.reconfigure を try/except でラップ済み(pythonw対応済み)

## mail_pipeline.py冒頭の主要処理
1. import imaplib, email, requests, jpholiday 等
2. skill_reader/skill_reader と usage_tracker/cost_logger をimport
3. config/.envをdotenv_values()で読み込み、os.environにマージ
4. IMAP_SERVER='mail65.onamae.ne.jp'、IMAP_PORT=993 を設定
5. EMAIL_ACCOUNTS リストを構築(共通+松野+岡本)
6. FETCH_LIMIT=50, PROCESS_LIMIT=10, DAILY_COST_LIMIT_USD=2.0
7. その後main()でIMAP接続→メール取得→処理

## 観測仮説
- A: PCがスリープしていて、復帰直後の11:13に発火。復帰直後のネットワーク未確立でIMAP接続失敗
- B: IMAP DNS解決失敗(mail65.onamae.ne.jp → IP化が必要、userMemoriesに「118.27.122.112を使え」と既知)
- C: stdout/stderrバッファがflushされる前にプロセス強制終了
- D: 17秒は某APIタイムアウトのデフォルト値(IMAP/HTTPS) → 接続タイムアウト後に黙って死亡

# Round4の問い

Q1. 17秒で原因不明死亡の最も疑うべき原因はどれか。A/B/C/D以外もあれば挙げよ。
Q2. 12:00 Cron(あと30分)を待たずに手動実行で原因究明すべきか。あるいは12:00 Cron観測を優先すべきか。
Q3. 手動実行する場合、副作用(Notion登録、メール取得)を最小化しつつ原因切り分けする最短手順を示せ。
Q4. 仮説Bが当たりなら、`.env`の`OUTLOOK_IMAP_SERVER`をIPに書き換えるか、`/etc/hosts`相当を使うか、どちらが安全か。
Q5. 仮説Aが当たりなら(復帰直後の不安定)、対策はWindowsスリープ無効化かタスクの起動条件変更か。CEOに上げるべき粒度で評価。
Q6. ジョブズが今この場で自走判断で取れるアクションと、CEO確認が必要なアクションを分けよ。

簡潔・断言・実行可能なコマンド付き。
"""

resp = client.responses.create(model="gpt-5.4", reasoning={"effort": "low"}, max_output_tokens=12000, input=PROMPT)

out_text = ""
for item in resp.output:
    if item.type == "message":
        for c in item.content:
            if c.type == "output_text":
                out_text += c.text

usage = resp.usage
in_t = usage.input_tokens
out_t = usage.output_tokens
cost = in_t * 1.25 / 1_000_000 + out_t * 10 / 1_000_000

header = f"=== wall_hitting bugs round4 by gpt-5.4 ===\nin={in_t} out={out_t} cost=${cost:.4f}\n\n"
result = header + out_text

out_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\auto_coder\wall_hitting_bugs_round4.txt"
with open(out_path, "w", encoding="utf-8") as f:
    f.write(result)

print(header)
print(out_text)
