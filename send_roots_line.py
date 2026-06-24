import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import requests
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
LINE_TOKEN = config["LINE_CHANNEL_ACCESS_TOKEN"]
MATSUNO_ID = config["MATSUNO_LINE_USER_ID"]
OKAMOTO_ID = config["OKAMOTO_LINE_USER_ID"]

NOTION_URL = "https://www.notion.so/Roots-36d450ff37c081218e5fe40032f14ddc"

RAW = """■案件名 基幹システム移行支援

■期間 6月～

■勤務形態 リモート併用（八丁堀） ※週3日出社

■必須スキル ・要件定義経験5年以上

■尚可スキル ・java,springベースでの経験 ・Postgreの経験 ・フロントに立って顧客と直接の折衝経験 ・住宅系の知見 ・基幹システムの移行経験

■商流制限 貴社社員・貴社所属の個人事業主まで ※営業支援費対応が可能でしたら、貴社１社先まで

■年齢制限 50代前半まで

■外国籍 不可

■稼働率 100%

■単価 ～75万円 ※スキル見合い

■精算条件 精算有り　140-180h　上下割

■支払サイト 月末締め翌々月5日払い（35日）

■募集人数 1名

■面談回数 2回（Web）

■業務内容 住宅系のお客様基幹システムの移行にあたり、業務チームで要件定義を実施していただきます。システムはjava,springベース。DBはPostgre。対応範囲は要件定義～詳細設計を想定しております。

■備考 ・短期（6カ月以内）が多い方はNGです ・長期で参画可能な方のみ ・服装：オフィスカジュアル

■お願い ご提案いただく際に、必須・尚可のマッチ度（可能でしたらスキルコメントも）をお教えください。"""

MESSAGE = f"""【新着案件】基幹システム移行支援（Roots）

【要約】
単価: ～75万円（スキル見合い）
期間: 6月〜（長期）
勤務: リモート併用・八丁堀、週3出社
面談: 2回（Web）
外国籍: 不可
必須: 要件定義経験5年以上
尚可: Java/Spring・PostgreSQL・顧客折衝・住宅系知見・基幹移行経験
備考: 短期NG・50代前半まで・商流1社まで

Notion: {NOTION_URL}
──────────────
【原文】
{RAW}"""


def push(user_id, name, text):
    res = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={"Authorization": f"Bearer {LINE_TOKEN}", "Content-Type": "application/json"},
        json={"to": user_id, "messages": [{"type": "text", "text": text}]},
        timeout=10,
    )
    print(f"[{name}] status={res.status_code} response={res.text[:100]}")
    return res.status_code


push(MATSUNO_ID, "松野", MESSAGE)
push(OKAMOTO_ID, "岡本", MESSAGE)
