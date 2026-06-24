import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from openai import OpenAI
from dotenv import dotenv_values

env_path = os.path.join(os.environ["USERPROFILE"], "OneDrive", "\u30c7\u30b9\u30af\u30c8\u30c3\u30d7", "ses_work", "config", ".env")
env = dotenv_values(env_path)
client = OpenAI(api_key=env.get("OPENAI_API_KEY"))

prompt = """SES自動化システムのP1バグ修正8件の実装方針を判定してください。日本語で。
制約: Cursor(AI)が実装、同時2タスクまで、各タスクは小さく分割。

## P1タスク一覧

11. 備考フォールバックの結果待ちが2.0固定: 並行スコア計算で結果待ち日数分岐(1-2日=2.5, 3-7日=2.0, 8日+=0)が効かない。備考テキストから日数を抽出するパーサーが必要。

12. SQLite WAL未設定: pipeline(raw_inbox.db)とcost_guard(state.sqlite3)の両方。並列書き込み時のロック問題。接続時にPRAGMA journal_mode=WALを実行するだけ。

13. gate_checker v2.2: (a)フェーズ別モデルルーティング未実装 (b)Geminiが毎回ERRORでフォールバック→実質GPT単独判定 (c)DAILY_CALL_LIMIT=10だがSPECは30 (d)Notion APIにCostGuardを誤要求する問題(システムプロンプト改善)

14. LINE push残通数-1時にpush試行: push_or_logでremaining!=0判定→quota取得失敗(-1)でpush送信。remaining>0に修正。reply-onlyモード(残150通以下)も未実装。

17. needs_human_review層1キーワード不一致: 「費用が発生」「契約変更」が未登録。層3のHUMAN_REVIEW行欠落時のフォールバックなし。

18. スケジューラ二重共存: Windows Task SchedulerとPython scheduler.pyが独立して同じpipelineを起動。ファイルロックで排他制御を入れるか、片方を廃止。

19. IMAP接続タイムアウト未設定: imaplibデフォルト=無制限。リトライなし。

20. UTC/JST日付境界不整合: cost_guardはUTC、pipeline Layer2集計はJST。09:00前後でずれる。

### 質問
Q1: どの組み合わせで1つのCursorタスクにまとめるのが効率的か？依存関係を考慮。
Q2: #13のGeminiフォールバック問題は、APIキー/モデル名/レート制限のどれが原因か推測できるか？
Q3: #18のスケジューラ二重共存は、どちらを残すべきか？Task Scheduler vs Python scheduler.py。
Q4: 実装順序の推奨（Week4-5の2週間で完了する前提）。"""

print("o4-miniに壁打ち中...", flush=True)
resp = client.responses.create(
    model="o4-mini",
    input=[{"role": "user", "content": prompt}],
    reasoning={"effort": "medium"},
    max_output_tokens=8000
)
full_text = ""
for item in resp.output:
    if item.type == "message":
        for part in item.content:
            if hasattr(part, "text"):
                full_text += part.text
print(full_text)

out_path = os.path.join(os.environ["USERPROFILE"], "OneDrive", "\u30c7\u30b9\u30af\u30c8\u30c3\u30d7", "ses_work", "research_results", "GPT_WALLHIT_P1.md")
with open(out_path, 'w', encoding='utf-8') as f:
    f.write("# GPT壁打ち: P1タスク実装方針\n実行日: 2026-06-19\n\n")
    f.write(full_text)
