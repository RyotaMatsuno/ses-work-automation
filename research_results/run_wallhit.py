import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import dotenv_values
from openai import OpenAI

env_path = os.path.join(
    os.environ["USERPROFILE"], "OneDrive", "\u30c7\u30b9\u30af\u30c8\u30c3\u30d7", "ses_work", "config", ".env"
)
env = dotenv_values(env_path)
client = OpenAI(api_key=env.get("OPENAI_API_KEY"))

system_prompt = """あなたはSES事業の技術顧問です。2名体制の小規模SES会社の自動化システム群の包括調査結果をレビューし、経営判断に資する優先順位付けと具体的な対処方針を提示してください。

制約:
- CEO松野は技術者ではない。LINEとClaudeだけで業務完結する設計
- コード実装はCursor（別AI）が担当。ここでは「何を・どの順で・なぜ」を決める
- 月のAPI予算は$140、日次$8が上限
- 稼働者15名弱、月500件以上のメール流入
- 営業インフラの信頼性が最優先（案件取りこぼし＝売上損失に直結）
- 日本語で回答してください"""

user_prompt = """以下は全9システムの包括調査（R01〜R15）から抽出した重大発見20件です。
各項目の番号は調査レポート番号ではなく発見の通し番号です。

## カテゴリA: コスト暴走・データ欠損リスク（事業直撃）

1. pipelineがCostGuard v2未統合: mail_pipelineのBatch API経路はコスト記録すらバイパス。独自の$2/日制限のみで、get_today_cost_usd()が例外時$0.0を返すfail-open設計。6/15に$3.98/日を記録（$2制限が機能していなかった実績あり）。catch-up時（バックログ1000件+）に$3超のリスク。

2. Notion登録失敗でも再処理不可: register_project()失敗後もfinally節でsave_processed_id()が走り、processed=1になる。案件データの永久欠損リスク。common/notion_register.pyに429リトライ+upsertがあるが未使用。

3. importer毎回exit 255クラッシュ: Task Scheduler jobz_importerが30分おきに起動するが、毎回途中で死亡（16:52起動→26件登録→16:59停止）。ログ不在。

4. pipeline Batch APIにコスト記録なし: classify_email_v2のBatch API直接呼び出しはlog_cost()をバイパス。月次コスト集計が実態を反映しない。

## カテゴリB: マッチング精度・営業影響（成約率に直結）

5. 語彙外必須スキル31件が自動パス→MATCH化: SkillNormalizerが正規化できないスキル（Terraform、SAP等）はチェック対象外になり、必須スキル不足でもMATCH通知される。

6. soft-skill all-pass未実装: 承認済み方針「ソフトスキルは全員○」が未実装。PM/コミュ力等がambiguous_skillsとしてREVIEWトリガーか語彙外パスでMATCH化。

7. 並行情報の当日確認チェック未実装: 事業ルール「当日確認分のみ有効」のロジックなし。

8. Notion 400フォールバックで全員マッチング対象: 提案対象フラグフィルタ失敗時に全エンジニアを取得。過去実績あり。

9. BTM/NBW案件がengineer判定→skip: パターン【BTM|【NBWが【BTM案件】にも誤マッチ。案件取りこぼし。

10. 尚可スキル+2万上振れ・7万目標粗利・5万超乖離チェックが未配線。

11. 備考フォールバックの結果待ちが2.0固定（日数分岐が効かない）。

## カテゴリC: インフラ・運用リスク

12. SQLite WAL未設定（pipeline/cost_guard両方）
13. gate_checker v2.2未実装（フェーズ別モデル・装置2/3）
14. LINE push残通数-1時にpush試行（バグ）
15. freee_invoice_monthly.pyが承認ゲートなしで並行稼働（60日バケット"46"バグ付き）
16. FT階段粗利75%/80%未実装（一律68%）
17. needs_human_review層1キーワードが仕様と不一致
18. スケジューラ二重共存（TaskScheduler + Python scheduler）
19. IMAP接続タイムアウト未設定・リトライなし
20. UTC/JST日付境界不整合

---

以下5問に具体的に回答してください。

Q1: P0/P1/P2の分類。全20項目を分類し、各項目に1行の理由をつけてください。

Q2: P0各項目について、Cursorに投げるCLAUDE.md/SPEC.md/TASKS.mdレベルの作業指示の骨子を示してください。具体的なファイルパスと修正方針を含めること。

Q3: マッチング精度問題のグルーピング
- 語彙外スキルsilent passとsoft-skill all-passは1タスクか別タスクか？理由付きで。
- 並行情報の当日確認は、Notion並行案件データ取得が先か、備考パーサー改善が先か？

Q4: 相互依存やリスク連鎖で見落としているものはあるか？特に「AをBより先に直さないと、Bの修正が無駄になる」パターン。

Q5: 2名体制・月$140・Cursor実装という制約で、Week1/Week2/Week3-4のバッチ分割案を出してください。各Weekの同時並行Cursorタスク数の上限は2。"""

print("GPT o4-miniに壁打ち中...", flush=True)

resp = client.responses.create(
    model="o4-mini",
    input=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
    reasoning={"effort": "medium"},
    max_output_tokens=12000,
)

full_text = ""
for item in resp.output:
    if item.type == "message":
        for part in item.content:
            if hasattr(part, "text"):
                full_text += part.text

print("\n" + "=" * 80)
print("GPT o4-mini 壁打ち結果")
print("=" * 80)
print(full_text)

out_path = os.path.join(
    os.environ["USERPROFILE"],
    "OneDrive",
    "\u30c7\u30b9\u30af\u30c8\u30c3\u30d7",
    "ses_work",
    "research_results",
    "GPT_WALLHIT_RESULTS.md",
)
with open(out_path, "w", encoding="utf-8") as f:
    f.write("# GPT壁打ち結果: 全システム調査優先順位付け\n")
    f.write("実行日: 2026-06-19\nモデル: o4-mini (reasoning effort: medium)\n\n")
    f.write(full_text)
print(f"\n保存先: {out_path}")
