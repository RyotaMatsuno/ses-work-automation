# -*- coding: utf-8 -*-
"""
GPT-5.4 Round3 壁打ち
目的: 松野が今すぐ手を動かす作業の最終確定。Round1/Round2の合意を踏まえて、
本当に「今夜・松野手作業」が必要なものだけに絞る。
"""

import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

PROMPT = """
あなたはSES営業基盤のシニア技術レビュアー。Round1/Round2の続きで、最終確定のRound3です。

# 前提
- Round1で全体評価・優先順位確定済み
- Round2で「matching_v2切り離しA1-α」は妥当、`UseUnifiedSchedulingEngine=false`への変更は今夜避けるべき、と合意
- 19:00/20:00両方のCronがスキップされたことが判明(Operational Log無効化で原因究明不可)
- jobz-watchdog小文字版は一般権限で停止不可。Round2は「今夜は保留、CEO帰還後管理者で削除」推奨

# Round3で確定したい問い
**松野(CEO)が今すぐ管理者PSを開いて手を動かす必要がある作業はどれか。**

## 候補リスト
1. Operational Log有効化
   `wevtutil sl Microsoft-Windows-TaskScheduler/Operational /e:true`
   - 目的: 次のスキップで原因が分かるようになる
   - リスク: ほぼゼロ(ログ有効化のみ)

2. StartWhenAvailable=true 設定
   - 目的: PCがスリープ等で発火逃しても復帰時に拾う
   - リスク: 低(挙動マイルドに変わる程度)
   - Round2は「今回のQueued短縮には直結しないが効果候補」と評価

3. UseUnifiedSchedulingEngine=false 設定
   - 目的: 新エンジンの発火スキップ問題回避
   - リスク: タスク再作成レベルの変更
   - **Round2は「今夜は触る優先度低」と評価**

4. jobz-watchdog小文字版 delete
   `schtasks /delete /tn "<小文字版タスク名>" /f`
   - 目的: ノイズ除去
   - リスク: ほぼゼロ
   - Round2は「業務影響なし、今夜は保留可」と評価

5. A1-α(matching_v2切り離し)維持の明示承認
   - 既に実装済み、20:00以降反映
   - リスク: なし
   - 確認のみ

6. PROCESS_LIMIT Day1=20 昇格
   - Round2は「4連続OK確認後、まだ早い」と評価

# 質問
Q1. 上記6つのうち、本当に「今夜・松野手作業」が必要なのはどれか。優先順位付きで明示せよ。
Q2. 逆に「CEO帰還後でいい」「自走で済む」「不要」と分類すべきものはどれか。
Q3. 各「今夜やる」項目について、貼るだけで完結する管理者PowerShellコマンド一行ずつを示せ。
   (パラメータ未確定の項目はTODO明示)
Q4. 万一今夜の手作業中に何かが壊れた場合のロールバック手順を、各項目について1行で。
Q5. Round2で「触るな」と言われた項目を、Round3でも維持すべきか、それとも変更すべきか。

簡潔・断言ベース。長文より「松野作業リスト」が出口。
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
# gpt-5.4 pricing(参考): in $1.25/M, out $10/M
cost = in_t * 1.25 / 1_000_000 + out_t * 10 / 1_000_000

header = f"=== wall_hitting bugs round3 by gpt-5.4 ===\nin={in_t} out={out_t} cost=${cost:.4f}\n\n"
result = header + out_text

out_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\auto_coder\wall_hitting_bugs_round3.txt"
with open(out_path, "w", encoding="utf-8") as f:
    f.write(result)

print(header)
print(out_text)
