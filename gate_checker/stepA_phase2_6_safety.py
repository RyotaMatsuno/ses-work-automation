"""
Step A Phase②.6: 追加安全装置4つの設計レビュー
o3-miniで実装設計の妥当性、o3で経営観点の精査(2段階)
"""

import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import os
from pathlib import Path

from openai import OpenAI

env_path = Path("config/.env")
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip().strip('"')

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

SAFETY_DEVICES = """
# 追加安全装置4つ(B案段階解放と併設)

## 装置1: ledger.py 前回比急増検知
- 仕様: ledger.pyに各実行のコストを記録、前回実行比2倍以上ならLINE警告
- 発動条件: 前回コスト × 2 < 今回コスト
- 通知先: 松野公式LINE(既存push_or_log使用)
- 実装場所: common/ledger.py の record() 関数内

## 装置2: gate_checker 1リクエスト$0.05超警告
- 仕様: gate_check.py 実行ごとに想定コスト計算、$0.05超でLINE警告
- 計算式: prompt_tokens × 入力単価 + completion_tokens × 出力単価
- 発動条件: 単発リクエスト > $0.05
- 通知先: 松野公式LINE
- 実装場所: gate_checker/gate_check.py のAPI呼出後

## 装置3: CostGuard停止時の自動Issue起票
- 仕様: CostGuardが$8/日上限で停止したら、Notion AI作業キューDBに自動起票
- 起票内容: 停止時刻、累積コスト、最後の実行ファイル、推定原因
- 通知先: Notion DB 37a450ff-37c0-819a-981b-c2e06ed282bb
- 実装場所: cost_guard.py の自動停止トリガー内

## 装置4: 自動ロールバック
- 仕様: 平均単価が想定の2倍超なら、DAILY_CALL_LIMITを前週値に自動戻す
- 想定平均: 約$0.008/call
- 発動条件: 1日平均単価 > $0.016
- 動作: config値を1段前に書き換え + LINE通知
- 実装場所: gate_checker/limit_controller.py (新規)

# 環境前提
- 通知系: 松野公式LINEのみ(月200通上限、push_or_log使用)
- Notion DB: AI作業キュー稼働中
- ledger.py: 既存(全スクリプト横断コスト集計)
- CostGuard: 稼働中($8/日・$140/月)
- 松野は手動操作を最小化したい(LINEで完結が大原則)
"""

PROMPT_R1 = f"""
あなたは実装設計の専門家。以下の4つの追加安全装置を実装観点で精査せよ。

{SAFETY_DEVICES}

【精査観点】
1. 各装置の発動条件は適切か?(過敏/鈍感のリスク)
2. 通知の集中(警告4種全部LINEに来る)で通知疲労や月200通上限を圧迫しないか?
3. 装置1と装置2は重複していないか?(両方ともコスト警告)
4. 装置4の「自動ロールバック」が誤発動するシナリオは?
5. 4つを同時実装する優先順位は?(MVP的に絞れるか)
6. ジョブズ・松野・岡本のオーナーシップは明確か?
7. 各装置の実装難易度と工数見積(時間単位)

【出力形式】
## 致命的問題(あれば)
## 4装置の重複・矛盾
## 通知設計の問題
## 優先順位とMVP案
## GO/HOLD/NG判定
## 必須修正事項
"""

print("=" * 60)
print("ラウンド1: 実装設計レビュー (o3-mini)")
print("=" * 60)

response = client.chat.completions.create(
    model="o3-mini",
    messages=[{"role": "user", "content": PROMPT_R1}],
    reasoning_effort="medium",
)
r1_result = response.choices[0].message.content
print(r1_result)
print()
r1_cost = response.usage.prompt_tokens * 1.1 / 1_000_000 + response.usage.completion_tokens * 4.4 / 1_000_000
print(f"ラウンド1コスト: ${r1_cost:.4f}")
print()
print("=" * 60)
print("ラウンド2: 経営観点最終裁定 (o3)")
print("=" * 60)

PROMPT_R2 = f"""
SES営業自動化システムの追加安全装置4つについて、
実装観点(o3-mini)のレビューが下記の通り出た。経営観点で最終裁定せよ。

【元の4装置仕様】
{SAFETY_DEVICES}

【o3-miniのレビュー】
{r1_result}

【経営観点での裁定指示】
1. 4装置のうち、月コスト削減効果と事故防止効果のROIで優先順位を決めよ
2. MVPとして最初の1週間で実装する装置を1〜2個に絞れ
3. 残り装置は何週目に実装するか明示
4. 通知設計(LINE月200通上限)で最適な発動閾値を提案
5. 「これだけは絶対外すな」を1つ挙げよ
6. 全装置実装後の月コスト変動見込み

【出力形式】
## 最終裁定結論(3行)
## MVP装置(1〜2個)
## 段階実装ロードマップ
## 通知閾値設計
## 絶対譲るなポイント
## 月コスト変動見込み
"""

response = client.chat.completions.create(
    model="o3",
    messages=[{"role": "user", "content": PROMPT_R2}],
    reasoning_effort="high",
)
r2_result = response.choices[0].message.content
print(r2_result)
print()
r2_cost = response.usage.prompt_tokens * 2 / 1_000_000 + response.usage.completion_tokens * 8 / 1_000_000
print(f"ラウンド2コスト: ${r2_cost:.4f}")
print(f"2ラウンド合計: ${r1_cost + r2_cost:.4f}")
