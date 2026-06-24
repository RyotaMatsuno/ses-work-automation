# -*- coding: utf-8 -*-
"""バグA1/A2/B1の壁打ち round1: 全体評価と優先順位
GPT-5.4 で詳細レビュー。
"""

import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import os
from pathlib import Path

from openai import OpenAI

BASE = Path(__file__).resolve().parents[1]
env_path = BASE / "config" / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip().strip('"')

sys.path.insert(0, str(BASE))
from common.ledger import can_spend, daily_total, record

MODEL = "gpt-5.4"
PRICE_IN = 2.5 / 1_000_000
PRICE_OUT = 15.0 / 1_000_000
MAX_OUT = 12000

# 引き継ぎ内容と発見したバグの完全な詳細
PROBLEM = """
# 事業背景
SES(System Engineering Service)個人事業。CEO松野とパートナー岡本の2名体制。AIエージェント「ジョブズ」が松野の参謀。
契約先: TERRA(粗利80%)・フラップテック(階段契約 現在68%、あと2件で75%)。月500件以上の案件メール処理を自動化中。
インフラ: Windows + Python 3.12 + jobz-commandサーバー(localhost:8765) + Notion DB + LINE Messaging API + Anthropic Claude API + OpenAI API + Gemini API。
全LLM呼び出しは common/ledger.py の cost guard(daily $8 / monthly $140)経由。

# 直近の重大インシデント(2026-06-17 17:00過ぎに発覚)
案件登録が 6/13〜6/17 ほぼゼロ。7日間平均179件のところ 6/13-14と6/16-17は0件。
真の根本原因: SES_MailPipeline タスクスケジューラ自体が 2026-06-15 19:00 以降「無効」だった。
副次原因: 6/16 11:54 のコード修正(mail_pipeline.py 67567→65094bytes / +119行)が Notion 500 を誘発したため、緊急に無効化されていた可能性。

# 引き継ぎ時点(18:30)の対応
1. 現状版を mail_pipeline.py.bak_emergency_20260617_182923 でバックアップ
2. mail_pipeline.py.bak_phase4(6/4版・v5.1)へロールバック
3. PROCESS_LIMIT 50→10 / FETCH_LIMIT 200→50 へ縮小
4. SES_MailPipeline タスク再有効化(Next Run 19:00予定、1時間Cron)
5. matching系3タスク(jobz_matching_daily/SES_MatchingAndNotify/SES_MatchingV3)は元から無効、そのまま
6. 手動疎通確認 OK: 149件取得 / 138件新規 / Batch API 2バッチ送信、Notion 500 出ず

# ジョブズが引き継ぎ後に「他のバグチェックを入念に」と指示され発見した3つの追加バグ

## バグA1: run_pipeline.bat が壊れた matching_v2 を毎時起動し続ける

### 発見手順
- SES_MailPipeline タスクは wd_mail_pipeline.bat を呼ぶ
- wd_mail_pipeline.bat の中身は: python weekday_guard.py cmd /c "%~dp0mail_pipeline\\run_pipeline.bat"
- weekday_guard.py は土日祝日チェック(jpholidayがあればis_holiday判定)、平日なら argv[1:] を subprocess で実行
- run_pipeline.bat の中身:
  ```
  @echo off
  chcp 65001 >nul
  cd /d "%~dp0.."
  echo ===== mail_pipeline 開始 ===== >> mail_pipeline\\pipeline.log
  python -P mail_pipeline\\mail_pipeline.py >> mail_pipeline\\pipeline.log 2>&1
  if %ERRORLEVEL% NEQ 0 ( ... 失敗ログ ... exit /b 1 )
  echo ===== matching_v2 開始 ===== >> mail_pipeline\\pipeline.log
  python matching_v2\\matching_v2.py >> mail_pipeline\\pipeline.log 2>&1
  if %ERRORLEVEL% NEQ 0 ( 失敗(続行) ) else (
    notify_line.py 実行
  )
  ```
- つまり mail_pipeline.py の後に必ず matching_v2/matching_v2.py を実行する
- matching_v2 は 6/15 19:10 以降 JSONDecodeError(Expecting ',' delimiter: line 446 column 4 char 16673)で失敗継続
- 原因は matching_v2/skill_judge.py の Claude haiku 呼び出しで max_tokens=8000 限界に達して JSON が切断されているため
- pipeline.log には [2026/06/15 19:10:16.76] matching_v2 失敗(続行) という記録あり
- cost_log.jsonl には 2026-06-15T10:10:16 の matching_v2_skill_judge 記録があり、output_tokens: 8000(上限ピッタリ), cost_usd: 0.044281
- つまり毎時失敗するたびに 0.044ドル消費(年換算 約385ドル)
- マッチング処理自体は 6/15 以降完全停止していたが、CEOは「matching系3タスクは元から無効」と認識(誤認)

### 修正案A1-α: run_pipeline.bat から matching_v2/notify_line セクションを削除
- 影響範囲: マッチング機能が完全に消える(現在も実質止まっているので影響なし)
- ロールバック: 容易(bat編集だけ)
- リスク: 低

### 修正案A1-β: run_pipeline.bat を変更せず matching_v2.py 自体に早期exit追加
- matching_v2.py の冒頭で sys.exit(0) すれば失敗ログもコストもゼロに
- 影響範囲: 同上
- ロールバック: 容易
- リスク: 低

### 修正案A1-γ: matching_v3 を有効化して切替
- skill_judge を修正済の matching_v3 に置換
- 影響範囲: マッチング機能復活、ただし新たな問題発生リスクあり
- リスク: 中
- 現時点で急がない(別タスクとして計画済み)

## バグA2: 19:00 Cron が走らなかった

### 状況
- 18:29:23 に SES_MailPipeline タスクを再有効化
- 19:00 起動予定だったが、19:03 現在 pipeline.log の最新は 18:31:22(手動疎通)で止まっている
- schtasks /query 結果:
  - SES_MailPipeline Last Run Time: 2026/06/15 19:00:01(6/15が最後のまま)
  - Next Run Time: 2026/06/17 20:00:00(19:00をスキップして20:00に進んでいる)
  - Status: Ready / Last Result: 0
- XMLの主要設定:
  - DisallowStartIfOnBatteries: true
  - StopIfGoingOnBatteries: true
  - ExecutionTimeLimit: PT1H(1時間)
  - MultipleInstancesPolicy: IgnoreNew
  - UseUnifiedSchedulingEngine: true
  - StartBoundary: 2026-05-08T00:00:00
  - Repetition Interval: PT1H

### 推定原因(複数あり得る)
1. DisallowStartIfOnBatteries=true で 19:00 時点でバッテリー駆動だった → 起動失敗
2. ENABLE 直後の trigger 再計算で 19:00 がスキップされた(Windows Task Schedulerの既知挙動)
3. 19:00 起動はしたが何かのエラーで Last Run Time 更新前に終了した
4. MultipleInstancesPolicy=IgnoreNew で何か前のインスタンスが残っていた

### 修正案A2-α: schtasks /Run /TN SES_MailPipeline で手動起動テスト
- 即座に確認できる
- 結果次第で原因切り分け
- リスク: 低

### 修正案A2-β: DisallowStartIfOnBatteries=false に設定変更
- バッテリー駆動でも起動する設定
- 影響: 電源接続切れ時にCPU負荷で電池消耗するリスク
- リスク: 低〜中(ノートPC運用上の判断)

### 修正案A2-γ: 20:00 まで様子見
- 何もしない
- 1時間待ち
- リスク: ゼロだが時間ロス

## バグB1: jobz-watchdog 重複登録

### 状況
- jobz-watchdog (小文字版): Last Result -2147024894(0x80070002 = ファイル未発見), 5分毎にエラー継続
- JobzWatchdog (CamelCase): Last Result 0, 5分毎に正常終了
- 同じ機能の watchdog が2つ登録されている
- 小文字版が何のファイルを探して失敗しているかは未確認(start_server.bat の path 変更か?)

### 修正案B1-α: schtasks /delete /tn "jobz-watchdog" /f で削除
- 影響範囲: 5分毎のエラーログ消失、機能影響なし(CamelCase版が動いているため)
- リスク: 低
- ロールバック: 復元が手間(タスク再登録が必要)

### 修正案B1-β: schtasks /change /tn "jobz-watchdog" /disable で無効化
- 削除せず無効化
- ロールバック: 容易(/enable で復活)
- リスク: 最低

### 修正案B1-γ: 小文字版が指している実体ファイルを修正
- どのファイルを探しているか調査が必要
- 工数: 中
- リスク: 低

# GPT-5.4 への質問
以下4点について、SES個人事業の現場運用と Windows Task Scheduler / Python バッチ運用の知見から、優先順位と推奨アクションを示してください。

質問1: A1/A2/B1のうち、CEO不在中(数時間以上の自走時間)にジョブズが独自判断で進めるべきは何か。「独自判断OK」「CEO確認必須」を明示。
質問2: 各バグの修正案 α/β/γ の中でどれが最善か。理由を含めて。
質問3: 修正後の検証手順(20:00 Cron 復活確認、matching_v2 削除確認、watchdog エラー消失確認)を具体的に。
質問4: ここに挙げていない潜在バグ・盲点があれば指摘してください。
特に「ロールバック後の v5.1(6/4版)が、6/4〜6/15 の間に他システム側で行われた仕様変更(Notion DBスキーマ・LINE通知フォーマット・freee連携等)と齟齬を起こさないか」という観点を重視してください。

回答は実務的で簡潔に。要素ごとに見出しを切ってください。
"""

est_in = len(PROBLEM) // 3 + 1500
est_cost = est_in * PRICE_IN + MAX_OUT * PRICE_OUT
print(f"=== wall_hitting bugs round1 by {MODEL} ===")
print(f"Estimated input tokens: {est_in}")
print(f"Worst-case cost: ${est_cost:.4f}")
print(f"Today total: ${daily_total():.4f}")

if not can_spend(est_in, MAX_OUT, MODEL):
    print("[CostGuard] limit reached")
    sys.exit(1)

SYSTEM = """あなたは現場運用に長けたPython/Windows/SES業務の専門家エンジニアです。
SES個人事業のAIエージェント(ジョブズ)が、CEO不在中の自走判断のために壁打ちを求めています。
判断の精度と実行可能性を最優先に、簡潔かつ具体的に回答してください。
不確実な点は明示し、断定すべきでない箇所では「要確認」と書いてください。
推測を避け、コードや設定の根拠に立脚して論じてください。"""

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

try:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": PROBLEM},
        ],
        max_completion_tokens=MAX_OUT,
        reasoning_effort="low",
    )
except Exception as e:
    print(f"reasoning_effort failed: {e}")
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": PROBLEM},
        ],
        max_completion_tokens=MAX_OUT,
    )

result = response.choices[0].message.content or ""
usage = response.usage
actual_cost = usage.prompt_tokens * PRICE_IN + usage.completion_tokens * PRICE_OUT
record(usage.prompt_tokens, usage.completion_tokens, MODEL, "wall_hitting_bugs_round1")

print(f"\nContent length: {len(result)}")
print("=" * 60)
print(result if result else "(EMPTY)")
print("=" * 60)
print(f"Actual cost: ${actual_cost:.4f} (in={usage.prompt_tokens}, out={usage.completion_tokens})")
print(f"Today total: ${daily_total():.4f}")

out_path = BASE / "auto_coder" / "wall_hitting_bugs_round1.txt"
out_path.write_text(
    f"=== wall_hitting bugs round1 by {MODEL} ===\n"
    f"in={usage.prompt_tokens} out={usage.completion_tokens} cost=${actual_cost:.4f}\n\n"
    f"{result}\n",
    encoding="utf-8",
)
print(f"Saved: {out_path}")
