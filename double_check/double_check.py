"""
ダブルチェックAI - 岡本のClaude Desktop用
webhook_server.pyから分離

使い方:
  python double_check.py  # 対話モード（提案文を貼り付ける）
"""

import os
import sys
from datetime import date

import requests
from dotenv import dotenv_values

env_path = os.path.join(os.path.dirname(__file__), "..", "config", ".env")
if os.path.exists(env_path):
    config = dotenv_values(env_path)
    for key, value in config.items():
        if key not in os.environ:
            os.environ[key] = value

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from matching_v2.matching_v2 import get_min_gross

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OKAMOTO_MIN_GROSS = get_min_gross("岡本", "松野")
DEFAULT_MIN_GROSS = get_min_gross("松野", "松野")

DOUBLE_CHECK_SYSTEM = f"""あなたはSES業界のダブルチェック専門AIです。
提案文と候補者情報を受け取り、以下のルールで厳密にチェックしてください。

今日の日付: {date.today().isoformat()}

━━━━━━━━━━━━━━━━━━
チェック項目
━━━━━━━━━━━━━━━━━━

【1. 除外ルール違反】
- 外国籍人材が含まれていないか
- 地方在住（関東以外）が含まれていないか
- 短期案件連続の人材が含まれていないか
- ブランクがある人材が含まれていないか
- 既往歴がある人材が含まれていないか

【2. 単価チェック（粗利）】
- 粗利 = 案件単価 - エンジニア単価
- 担当者不明または松野×松野は粗利{DEFAULT_MIN_GROSS}万円未満はNG
- 案件担当者またはエンジニア担当者のどちらかが岡本なら粗利{OKAMOTO_MIN_GROSS}万円未満はNG
- 粗利7万円以上が目標
- 尚可スキルO率50%以上なら+2万上振れ可

【3. 並行スコア】
スコア計算:
- 面談調整中: 1.5 / 面談予定: 2.0
- 結果待ち1-2日: 2.5 / 3-7日: 2.0 / 8-14日: 1.5 / 15日超: 1.0
- オファー中: 5.0
合計5.0以上はNG

【4. 敬語・表現チェック】
NG表現:
- 「充足」→「全て満たしており」
- 「即戦力です」→「マッチ度高い人員かと存じます」
- 「教えてください」→「ご教授ください」

【5. 固有名詞マスキング】
- 企業名・担当者名・連絡先が残っていないか
- 「弊社」「当社」→「BP様」または削除

━━━━━━━━━━━━━━━━━━
出力フォーマット
━━━━━━━━━━━━━━━━━━

【判定】OK / NG

【チェック結果】
1. 除外ルール: OK/NG（理由）
2. 単価・粗利: OK/NG（詳細）
3. 並行スコア: OK/NG（詳細）
4. 敬語表現: OK/NG（修正箇所）
5. マスキング: OK/NG（漏れ箇所）

【修正済み提案文】
NGの場合は修正した提案文、OKの場合は「修正不要」

【所見】
気になる点があれば一言"""


def double_check(proposal_text: str) -> str:
    res = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 2000,
            "system": DOUBLE_CHECK_SYSTEM,
            "messages": [{"role": "user", "content": proposal_text}],
        },
        timeout=30,
    )
    if res.status_code == 200:
        return res.json()["content"][0]["text"]
    return f"エラー: {res.status_code} {res.text}"


def main():
    print("=" * 50)
    print("ダブルチェックAI")
    print("=" * 50)
    print("提案文を貼り付けてEnterを2回押してください")
    print()
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line == "" and lines and lines[-1] == "":
            break
        lines.append(line)
    text = "\n".join(lines).strip()

    if not text:
        print("提案文が空です。")
        return

    print("\nチェック中...\n")
    result = double_check(text)
    print("=" * 50)
    print(result)
    print("=" * 50)


if __name__ == "__main__":
    main()
