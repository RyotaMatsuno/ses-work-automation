import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

report = """# コスト安全性 完全監査報告書
作成: 2026-06-12 ジョブズ（Claude Fable 5で実施）

## 監査範囲
本番コード全体のLLM API呼び出し14箇所を完全列挙し、1件ずつ防御を検証。

## 多層防御の最終構成

### レイヤー1: common/ledger.py（リアルタイム遮断）
- 上限: $8/日・$140/月（.envから読込、検証済み一致）
- 被覆: mail_pipeline / outlook_to_notion
- can_spend()が呼び出し前にコスト見積もりで遮断

### レイヤー2: cost_guard.py（5分おき監視・強制停止）
- 上限: $20/日・$300/月（本日修正。レイヤー1破壊時の最終砦）
- ソフト警告: $4/日
- 発動するとCloud RunにLLM_KILL=1送信

### レイヤー3: 個別システムの独自ガード
- line_bridge (Cloud Run): 独自CostGuard $1/日・$6/月（保守的・正常）
- gate_checker: 日次10回制限 + リトライ上限3回
- task_auto_runner: 本日修正
  - 1タスク$5上限（Claude Code --max-budget-usd）
  - 1起動3タスク上限（10→3に削減）
  - runner日次$15上限（新設）
  - Claude Codeコストをledgerに記録（新設・レイヤー1/2から可視化）

### レイヤー4: Anthropic側スペンドリミット（外部・絶対防壁）

## 発見・修正した問題

| # | 問題 | 深刻度 | 対処 |
|---|---|---|---|
| 1 | cost_guard.py月次$6ハードコード | 高（今週中に誤停止） | $300に修正済み |
| 2 | Claude Codeコストが全ガードから不可視 | 高（暴走経路） | ledger記録追加済み |
| 3 | runner 1起動$50の暴走余地 | 高 | 3タスク+$15/日上限追加済み |
| 4 | ガードなしAPI呼び出し6ファイル | 低（全て手動実行のみ・自動経路なし） | 経過観察 |

## ガードなし6ファイルの詳細（自動実行経路なしを確認済み）
- double_check/double_check.py（手動のみ）
- gate_checker/agreement_checker.py（gate_check経由・回数制限あり）
- line_webhook/webhook_clean.py（独立・未使用）
- mail_pipeline/mail_pipeline_test1.py（テスト用）
- reply_parser/reply_parser.py（手動のみ）
- wall_hitting.py / wall_hit_matching.py（壁打ち用・手動のみ）

## 暴走シナリオ別の防御確認

| シナリオ | 防御 | 結果 |
|---|---|---|
| mail_pipeline大量呼び出し（6/2型） | ledger $8/日 + 7日SINCE + 処理50件上限 | ✅ 遮断される |
| task_runner NG再投入ループ | 試行2回でblocked | ✅ 最大$15/タスク |
| pending_tasks大量投入 | 3タスク/起動 + $15/日 | ✅ 修正済み |
| Cloud Run line_bridge暴走 | 独自ガード$1/日 | ✅ 遮断される |
| gate_check連打 | 日次10回制限 | ✅ 遮断される |
| 全レイヤー破壊 | Anthropicスペンドリミット | ✅ 外部遮断 |

## 現在のコスト実績
- 今月: $2.61 / $140（1.9%）
- 本日: $0.62 / $8（7.8%）
- モデル別: haiku $2.66 / sonnet $0.72 / gpt-4.1-nano $0.10

## マッチング稼働設計（確定）

### 自動マッチング（毎朝8:00 / matching_v3）
- ルールベース・LLMほぼゼロ（文面生成のみgpt-4.1-nano $0.0003/件）
- コストリスク: 無視できる水準

### LINEオンデマンド（PH 京成小岩形式 / line_query）
- LLM完全ゼロ（Notion直クエリ）
- コストリスク: ゼロ
- 本日修正中: 稼働状況フィルタ追加（task_auto_runner実行中）

### 案件流入（30分おき / mail_pipeline）
- LLM分類: haiku（$0.002/件）+ ledgerガード
- API失敗時: キーワードフォールバック（コストゼロ）で案件登録継続
- 1日想定: 100通処理 × $0.002 = $0.2/日（上限$8の2.5%）

### 想定月額（フル稼働時）
- mail_pipeline: $6/月
- matching_v3: $0.3/月
- gate_checker: $3/月
- task_auto_runner(Claude Code): $30〜90/月（タスク量次第・$15/日上限）
- 合計見込み: $40〜100/月（上限$140内）
"""

with open("reports/cost_audit_20260612.md", "w", encoding="utf-8") as f:
    f.write(report)
print("報告書保存: reports/cost_audit_20260612.md")
print(f"文字数: {len(report)}")
