# -*- coding: utf-8 -*-
"""Round11: 案件全件取り込み + 月次動向分析の設計相談"""

import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

PROMPT = """
Round11。mail_pipelineの大幅改修の設計相談。

# 現状
mail_pipeline.py（1686行）はSES配信メールを処理するシステム。
- 毎時実行、3アカウントからメール取得
- 2段階分類: ①ルールベース（キーワードパターンマッチ）→ ②LLM（Claude Batch API, gpt-4.1-nano）
- LLMが「project」「engineer」と判定したもの→構造化→Notion DB登録
- 「skip」「other」と判定したもの→捨てる
- 結果: 1日6,000件受信中、Notion登録は26-31件/日

# CEOからの指示
1. **案件メールは全件取り込みたい**。今のLLM判定で弾かれている案件（事務、ヘルプデスク、ロースキル等）も取り込みたい
2. **業界動向分析を月1で行いたい**。どんな案件が多いか、単価トレンド、スキル需要等

# 制約
- コスト: gpt-4.1-nano + Batch API(50%割引)で現在$0.04/日。DAILY_COST_LIMIT=$2.0
- 処理量: sessalesだけで1時間243件。FETCH=200で82%カバー
- 6,000件/日のうち「案件メール」は数百件、残りは人員紹介・広告・メルマガ等
- Notion APIレート: 3 req/sec
- 実装はCursorに投げる。ここでは設計のみ

# 質問
Q1. 「案件全件取り込み」の最善アプローチは？
  A案: skip/other判定を廃止、全メールをproject扱いで構造化→Notion登録
  B案: 分類は維持、project判定の閾値を大幅緩和（「案件っぽいもの」も全部取り込む）
  C案: 分類は維持、skipされたものも「未分類案件」としてNotion別ステータスで登録
  D案: 別のアプローチ

Q2. 6,000件/日を全件取り込むとコストどうなる？
  - 分類だけ: 6000件 × ~100トークン = 600Kトークン/日
  - 構造化まで: 案件判定されたもの × ~500トークン

Q3. Notion DB側の設計変更は必要？案件6,000件/日は多すぎないか？

Q4. 月次動向分析の設計。どのデータをどう集計すれば有用か？
  - 単価分布（帯別件数）
  - スキル需要ランキング
  - リモート率推移
  - 外国籍可/不可の比率
  - 募集人数のトレンド

Q5. 段階的に進めるなら優先順位は？

短く断定で。
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
header = f"=== round11 by gpt-5.4 ===\nin={usage.input_tokens} out={usage.output_tokens} cost=${cost:.4f}\n\n"
result = header + out_text
with open(
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\auto_coder\wall_hitting_round11.txt", "w", encoding="utf-8"
) as f:
    f.write(result)
print(result)
