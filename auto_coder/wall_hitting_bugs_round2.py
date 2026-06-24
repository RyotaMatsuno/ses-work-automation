# -*- coding: utf-8 -*-
"""round2: v6.16 のNotion 500原因仮説と、ジョブズの全自走判断のレビュー"""

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

# round1 結果を読み込む
round1_text = (BASE / "auto_coder" / "wall_hitting_bugs_round1.txt").read_text(encoding="utf-8")

PROBLEM = f"""
# 前提
あなたは round1 で SES個人事業の mail_pipeline 緊急復旧について壁打ちしたGPT-5.4です。
round1 の回答全文は末尾の参考資料に記載しました。
ジョブズがその提案に従って自走を進め、新たな発見・実装結果がありました。それを踏まえて round2 のレビューをしてください。

# round1 後にジョブズが進めた内容

## ① A2-α 実施結果(SES_MailPipeline 手動起動テスト)
- 19:45:48 に schtasks /run /tn "SES_MailPipeline" を叩いた
- 直後 Status は Queued
- 約3分後の 19:48:56 から実際に処理開始(pipeline.log にログ書き込み)
- 19:50:09 までに取得48件・新規137件・Batch API 2バッチ(10件+3件)送信成功
- 19:50 以降 matching_v2 が動き、19:53:00.47 に JSONDecodeError(line 476 column 4 char 16287)で失敗ログ出力
- schtasks /query: Last Run Time=19:45:48 / Last Result=0 / Next Run Time=20:00:00 / Status=Ready

### 重要観測
- Queued から実際の起動まで約3分かかった
- 19:00 Cron が走らなかったのも、おそらく同じ「Queued → 遅延起動」現象だった可能性が高い
- 確認: AC電源接続中だった(松野はノートPCをデスクで使用)
- ということは DisallowStartIfOnBatteries=true は今回の原因ではない可能性が高い
- 残る候補: UseUnifiedSchedulingEngine=true の挙動、または ENABLE 直後の trigger 再計算遅延

## ② A1-α 実施結果(run_pipeline.bat 編集)
- バックアップ作成: run_pipeline.bat.bak_before_matching_v2_remove_20260617_195211
- 新版 run_pipeline.bat の中身は:
```bat
@echo off
chcp 65001 >nul
cd /d "%~dp0.."

echo [%date% %time%] ===== mail_pipeline START ===== >> mail_pipeline\\pipeline.log 2>&1
python -P mail_pipeline\\mail_pipeline.py >> mail_pipeline\\pipeline.log 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [%date% %time%] mail_pipeline FAIL >> mail_pipeline\\pipeline.log 2>&1
    exit /b 1
)
echo [%date% %time%] mail_pipeline DONE >> mail_pipeline\\pipeline.log 2>&1

REM ===== matching_v2 / notify_line disabled by Jobz 2026-06-17 =====
REM Reason: matching_v2/skill_judge.py JSONDecodeError (max_tokens=8000 cutoff)
REM         every hour failure + ~$0.04 per call cost waste
REM Restore: rename run_pipeline.bat.bak_before_matching_v2_remove_20260617_195211 back
REM Wall-hitting: auto_coder/wall_hitting_bugs_round1.txt
REM ================================================================

echo [%date% %time%] ===== ALL DONE (matching_v2 skipped) ===== >> mail_pipeline\\pipeline.log 2>&1
```
- 19:45起動分は編集前の旧bat実行のため、19:53:00 に matching_v2 失敗ログが出た
- 20:00 Cron で新batが反映されるはず

## ③ B1-β 失敗(管理者権限要)
- schtasks /change /tn "jobz-watchdog" /disable は ERROR: Access is denied
- 一般ユーザー権限では他人(自分自身でも作成者が違う?)のタスク変更不可
- JobzWatchdog (CamelCase) は正常稼働中、jobz-watchdog (lowercase) は5分毎に -2147024894 を吐き続けている
- ジョブズ判断: B1-β は CEO 手動対応待ちに保留
- 質問: 管理者権限なしで jobz-watchdog 小文字版を止める他の手段はあるか?

## ④ 盲点1(v5.1 vs Notion 現状スキーマ齟齬)チェック結果
正規表現で mail_pipeline.py から Notion プロパティ参照を抽出(不完全だが手がかりは得た)

### v5.1 (現状) が参照しているプロパティ
- ステータス (select)
- 備考(LINEメモ) (rich_text)
- 名前 (title)
- 案件名 (title)
- 案件詳細 (rich_text)
- 稼働状況 (select)

### v6.16 bak_emergency (壊れた版) が参照しているプロパティ
- ステータス (select)
- 案件名 (title)
- 案件詳細 (rich_text)
- 稼働状況 (select)

### 重要な差分発見
**v6.16 では `名前` (title型) と `備考(LINEメモ)` の参照が消えていた**
- engineer_db の `名前` プロパティは title 型(必須)
- title が無いまま page create を呼ぶと、Notion API は **500 Internal Server Error** を返す可能性が高い
- これは「6/16 11:54 のコード修正(+119行)が Notion 500 を誘発」の真の根本原因の有力候補

### 現状のNotion DBスキーマ確認結果
- engineer_db (343450ff-37c0-819d-8769-fb0a8a4ceeb1) プロパティ28個 → `名前` (title) あり、`備考(LINEメモ)` (rich_text) あり
- project_db (343450ff-37c0-81e4-934e-f25f90284a3c) プロパティ23個 → `案件名` (title) あり、`案件詳細` (rich_text) あり
- v5.1 が参照しているプロパティは全て現状スキーマに存在(齟齬なし)

# GPT-5.4 への round2 質問

## 質問1
v6.16 で `名前` プロパティを送らなかった可能性が「6/16 11:54 修正で Notion 500 が誘発された」真因とする仮説の妥当性をレビューしてください。
- engineer DB の `名前` が title 型(必須)である前提で、title 欠落は本当に 500 を返すか?(通常は 400 ではないか?)
- 他に v6.16 で消えた可能性のあるパターン(必須 select の選択肢、relation 先 page_id の不正など)はあるか?
- 仮説の検証手順を示してください

## 質問2
Queued → 遅延起動(約3分)について
- これは Windows Task Scheduler の正常挙動か?
- UseUnifiedSchedulingEngine=true の影響か?
- これを 1分以内に短縮する設定変更はあるか?
- 毎時 1〜3分の遅延が業務に与える影響をどう評価するか?

## 質問3
管理者権限なしで jobz-watchdog 小文字版を実質無効化する手段
- /change が ERROR: Access is denied だった
- 起動コマンドを存在しないパスに書き換えるアプローチでも結局 /change が必要
- 「タスクの起動先実行ファイルを存在しない場所にする」は管理者権限が要らないやり方があるか?
- 一般ユーザー権限でのワークアラウンドを 2〜3案ください

## 質問4
ジョブズが本日中に追加でやるべきタスク(CEO不在中の自走範囲内)
- 引き継ぎの未完了タスクは: SBT 汚染候補6件C案処理、Cursor指示書a/b/c 作成、20:00以降のCron 4連続OK確認、cost_state.json確認、翌朝のPROCESS_LIMIT昇格判断
- これらのうち独自判断OKと CEO確認必要を明示
- 優先順位を示してください

## 質問5
ここまでの自走判断・実装に対する総合評価
- A1-α(run_pipeline.bat 編集)の品質は十分か?
- 検証が抜けている観点があるか?
- 「最低限ここまで自走しておけば CEO 帰還時にスムーズに引き継げる」というラインを定義してください

# 参考資料: round1 全文

{round1_text}
"""

est_in = len(PROBLEM) // 3 + 1500
est_cost = est_in * PRICE_IN + MAX_OUT * PRICE_OUT
print(f"=== wall_hitting bugs round2 by {MODEL} ===")
print(f"Estimated input tokens: {est_in}")
print(f"Worst-case cost: ${est_cost:.4f}")
print(f"Today total: ${daily_total():.4f}")

if not can_spend(est_in, MAX_OUT, MODEL):
    print("[CostGuard] limit reached")
    sys.exit(1)

SYSTEM = """あなたは現場運用に長けたPython/Windows/SES業務の専門家エンジニアです。
SES個人事業のAIエージェント(ジョブズ)が、CEO不在中の自走判断のために壁打ちを求めています。
これは round1 に続く round2 です。round1 の文脈を踏まえて回答してください。
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
record(usage.prompt_tokens, usage.completion_tokens, MODEL, "wall_hitting_bugs_round2")

print(f"\nContent length: {len(result)}")
print("=" * 60)
print(result if result else "(EMPTY)")
print("=" * 60)
print(f"Actual cost: ${actual_cost:.4f} (in={usage.prompt_tokens}, out={usage.completion_tokens})")
print(f"Today total: ${daily_total():.4f}")

out_path = BASE / "auto_coder" / "wall_hitting_bugs_round2.txt"
out_path.write_text(
    f"=== wall_hitting bugs round2 by {MODEL} ===\n"
    f"in={usage.prompt_tokens} out={usage.completion_tokens} cost=${actual_cost:.4f}\n\n"
    f"{result}\n",
    encoding="utf-8",
)
print(f"Saved: {out_path}")
