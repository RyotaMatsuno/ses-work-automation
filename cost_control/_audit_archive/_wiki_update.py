import sys, requests, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from dotenv import dotenv_values
cfg=dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
KEY=cfg.get("NOTION_API_KEY")
PAGE="353450ff-37c0-8145-9e3e-d80c8c8ed594"
H={"Authorization":f"Bearer {KEY}","Notion-Version":"2022-06-28","Content-Type":"application/json"}
def t(s): return [{"type":"text","text":{"content":s}}]
def h2(s): return {"object":"block","type":"heading_2","heading_2":{"rich_text":t(s)}}
def b(s): return {"object":"block","type":"bulleted_list_item","bulleted_list_item":{"rich_text":t(s)}}
children=[
 h2("2026-06-05 APIコスト事故と恒久対策（cost_control）"),
 b("事故: 6/2に1日$50.88($31.65 mail_pipeline + $19.22 matching_v2)消費。原因=mail_pipeline処理上限の2000化＋配信スパム除外フィルタ不在→募集中案件が1,637→5,970件に膨張→matchingのトークン爆発。Anthropic月次上限到達で6/3以降API全失敗(400)。LINE松野も200通/月上限で6/2から通知停止。"),
 b("Phase1(no-regret): Sonnet合理化(skill_reader text抽出/outlook_to_notion/skill_judge fallbackをHaiku化)、モデル名env一元化(common/model_config.py: TEXT/VISION/STRUCTURER/MATCH_MODEL)、cost_guard横展開(common/ledger.py, 既定DAILY$1/MONTHLY$6, env可変)。"),
 b("Phase2(構造): 配信スパム除外フィルタ is_broadcast()(List-Unsubscribe/List-Id・フッタ語句・多数宛て15件のOR、許可リスト最優先)＋CLASSIFY_LIMIT=150。案件4営業日自動失効 cost_control/project_expiry.py、タスク SES_ProjectExpiry 毎朝7:00。"),
 b("一時対応: 募集中×取り込み7日超の1,637件を『終了』へプルーニング(物理削除なし)。matching_v3の自動実行を一時停止(プール清浄後に再有効化)。"),
 b("恒久ルール(重要): (1)Anthropic/OpenAI呼び出しは必ずledgerガードを通す。(2)mail_pipelineの取り込み上限を変える時は必ず配信フィルタとセット。(3)skill_judgeのfallbackにSonnetを使わない(Haiku限定orハードエラー)。(4)vision以外でSonnetを使わない。"),
 b("残タスク: Phase3(vision A/Bでvisionモデル確定＋7/1上限リセット後の実コスト計測→cost_guard値の本調整)。C3-2のコスト超過アラートはLINE復活(7/1)後にログ/ステータスファイル方式で実装。残存ハードコードモデル(double_check/webhook_server等)のenv集約。"),
]
r=requests.patch(f"https://api.notion.com/v1/blocks/{PAGE}/children",headers=H,json={"children":children},timeout=60)
print("wiki append status",r.status_code)
if r.status_code!=200: print(r.text[:400])
else: print("WIKI UPDATED ok, blocks:",len(children))
