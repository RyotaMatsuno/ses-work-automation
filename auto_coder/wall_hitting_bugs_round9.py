# -*- coding: utf-8 -*-
"""Round9: SBT/国保/信販 計9件の処理確定"""

import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

PROMPT = """
緊急Round9。Notion DBの汚染データ処理方針確定。

# 背景
2026-06-14〜15にmail_pipelineのdedup破損で「過去の終了済み案件」が「新着」として再登録された問題。前チャットでC案(IMAP実受信日確認後に「終了」化)で合意済みだが未実行。Notion DBの現状を確認した結果が以下:

# 対象データ(全件「募集中」のまま放置)

## SBT 5件(過去の終了済み案件とタイトル類似度0.85以上)
1. 37f450ff-...8194 | Prisma Access設計構築 | created 2026-06-15 08:02 JST
2. 37f450ff-...818e | 建設業向けのERPパッケージ導入(会計領域) | 2026-06-15 08:02 JST
3. 37f450ff-...8163 | テスト、ヘルプデスク、運用保守、データ移行@南行徳 | 2026-06-15 02:03 JST
4. 37f450ff-...8183(b755) | AWS案件/運用ツール構築/運用自動化@五反田 | 2026-06-15 01:03 JST
5. 37f450ff-...812e | AWS案件/運用ツール構築/運用自動化 | 2026-06-15 00:05 JST
6. 37f450ff-...811a | 置局サポート業務 | 2026-06-15 00:04 JST

(過去chatで「6件」と言っていたうち1件「業務サポート案件(PMO、業務整理)」は既に終了化済み。残り5件。
ところがクエリでは6件取れた。8183は同じprefix違うsuffix(91db=終了、b755=募集中)で別物。
結果: SBT汚染で実際に「募集中」のまま残っているのは5件 + 1件のAWS案件@五反田。計6件)

## 国保系 自己重複 2件(両方「募集中」)
- 37f450ff-...8119 | 国保向け健康保険組合向けシステム改修・保守(8月)
- 37f450ff-...8103 | 国保向け健康保険組合向けシステム改修・保守

## 信販系 自己重複 2件(両方「募集中」)
- 37f450ff-...81ad | 某大手信販会の運用保守(半年短期予定)
- 37f450ff-...8117 | 某大手信販会の運用保守

# 確認した事実
- これら計10件は全て「募集中」ステータスのまま
- matching_v3はこれらを「新着」として扱っており、マッチング通知済みの可能性あり
- 業務影響: 古い案件が「新着」として所属に意向確認メール送信される可能性
- DBにcreated_timeはあるが、元メールのDateヘッダ情報は「案件詳細」フィールドに本文として保存されている

# 質問

Q1. SBT 6件の処理判断
  - そのまま全件「終了」化していいか?(過去chatで類似度0.85以上=汚染確定と判定済み)
  - それとも一件ずつ「案件詳細」のメール本文Date確認してから判断すべきか?

Q2. 国保系2件・信販系2件の自己重複処理
  - 「(8月)」「(半年短期予定)」付きと「無印」のペア
  - どちらが新着・どちらが汚染か判定基準は?
    候補:
    (a) 無印が古い(汚染)、より詳細な「(8月)」「(半年短期予定)」が新着
    (b) 詳細な方が古い(過去の同案件の再投稿)、無印が新着
    (c) 案件詳細を読まないと判定不可
    (d) 両方とも案件詳細を読んで送信者と日付で判定

Q3. matching_v3への影響
  - これら10件にmatching_v3が既に意向確認メールを送信済みだった場合のリカバリ手順は?
  - cost_log.jsonlやNotion AI作業キューを確認する必要があるか?

Q4. 終了化のNotion API操作
  - ステータスプロパティ名: "ステータス"(select型 or status型)
  - 「終了」値で更新するPATCHリクエスト構造

Q5. 終了化と同時に「終了理由」をどこかに記録すべきか?
  - 案件詳細フィールド末尾に追記
  - 別プロパティ
  - 不要(ステータス変更だけで十分)

Q6. 実行順序の推奨
  - 全件一括 vs 1件ずつ確認
  - 副作用最小の順序は?

Q7. ジョブズ自走範囲の判断
  - これは「精度・品質が変わる」操作と判断して松野確認すべきか
  - それとも「過去合意済みのC案実行」として自走OKか
  - 判断分担ルール: 使い方変わる/コスト/精度品質が変わる→松野確認、それ以外は自走

短く断定、PATCH body例付き。
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
header = f"=== round9 by gpt-5.4 ===\nin={usage.input_tokens} out={usage.output_tokens} cost=${cost:.4f}\n\n"
result = header + out_text
with open(
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\auto_coder\wall_hitting_bugs_round9.txt", "w", encoding="utf-8"
) as f:
    f.write(result)
print(header)
print(out_text)
