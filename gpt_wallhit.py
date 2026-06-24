# -*- coding: utf-8 -*-
# GPT-4oへの壁打ち
import sys

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import dotenv_values

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
API_KEY = env.get("OPENAI_API_KEY", "")

prompt = """あなたはSES（システムエンジニアリングサービス）業界に詳しいコンサルタントです。

【現状】
- 2名体制のSES事業者
- sessalesメールに1日4,000〜5,000件の案件・人材情報メールが届く
- 現在は自作のmail_pipeline.py（Python）でIMAPで最新200件を30分ごとに取得してLLMで分類・Notionに登録
- LLMコスト: 月約$140（Anthropic claude-haiku使用）
- 課題: 4,000件中200件しか処理できていない（4.5%のカバー率）

【質問1】
日本のSES業界向けに、このようなメール自動取り込み・案件DB管理ができるSaaSはありますか？
以下の条件で教えてください：
- メールから案件情報を自動抽出してDBに登録できる
- 日本語対応
- 月額費用
- 代替手段として検討できるサービス名と概要

知っているサービス例：
- エンジニアルート、SES Cloud、Jobee、キャリアクロス、ミイダス、BizteX

【質問2】
月$140のLLMコストは高いですか？この規模（1日4,000件メール処理、2名体制）で代替できるアーキテクチャを提案してください。
- キーワードベース分類（LLM不使用）
- 安価なモデルへの切り替え
- 処理量を絞る戦略
それぞれのコスト試算と実現可能性を教えてください。

JSON形式で回答してください：
{
  "saas_options": [{"name":"","url":"","monthly_cost":"","mail_import":"","matching":"","notes":""}],
  "architecture_alternatives": [{"approach":"","est_monthly_cost":"","coverage":"","pros":"","cons":""}],
  "recommendation": ""
}"""

res = requests.post(
    "https://api.openai.com/v1/chat/completions",
    headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    json={"model": "gpt-4o", "max_tokens": 2000, "messages": [{"role": "user", "content": prompt}]},
    timeout=60,
)
if res.status_code == 200:
    text = (
        res.json()["content"][0]["text"] if "content" in res.json() else res.json()["choices"][0]["message"]["content"]
    )
    print(text)
else:
    print(f"エラー: {res.status_code} {res.text[:200]}")
