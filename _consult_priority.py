import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.getcwd())
from gate_checker.agreement_checker import _load_env, call_gemini, call_gpt4o_simple

env = _load_env()
openai_key = env.get("OPENAI_API_KEY", "")
gemini_key = env.get("GEMINI_API_KEY", "")

system_prompt = """あなたはSESビジネス自動化システムの技術アドバイザーです。
以下の2案を比較し、どちらを先に着手すべきか判定してください。
判定形式:
【推奨: A案】または【推奨: B案】
理由を3点以内で簡潔に。
"""

user_prompt = """## 状況
SES事業の経営参謀AI「ジョブズ」が、CEO松野からタスクを受けてCursorに実装指示書を流す体制を運用中。
現状は松野がCursorを手で開いてComposerに指示書を貼る作業が残っている。
松野の方針: 「全て自動化したい。松野がかかるタスクはなくす」

## 比較対象

### A案: auto_bug_watcher を先に完成させる
- 既にSPEC.md/TASKS.md/CLAUDE.md作成済み
- gate_checker ①通過済み（条件付きGO）
- pending_tasks/に指示書保存済み
- あとは松野がCursorに貼って実装させるだけ
- 完成すればログ監視→2AI診断→自動修正指示書生成のループが立ち上がる
- 実装見込み: Cursorで20〜30分

### B案: task_auto_runner（完全自動化基盤）を先に作る
- 新規SPEC設計から始める必要あり
- ジョブズが pending_tasks/ に保存 → Claude Code CLIが自動起動 → 完了検知 → ゲート②自動実行 → LINE通知のフロー
- 一度作れば auto_bug_watcher 含め以降の全タスクが完全自動化
- Claude Code CLI (claude --print)はインストール済み確認
- 実装見込み: 設計+実装+検証で2〜3時間

## 評価軸
1. ROIの大きさ
2. 松野の手作業削減効果（最優先）
3. 完成リスク（中断時の損失）
4. モメンタム（既に動いているA案を止めるべきか）

## 質問
A案とB案、どちらを先にやるべきか？
"""

print("=" * 60)
print("[GPT-4o]")
gpt_result = call_gpt4o_simple(system_prompt, user_prompt, openai_key)
print(gpt_result.text)
print(f"\n[エラー: {gpt_result.error}]" if gpt_result.error else "")

print("\n" + "=" * 60)
print("[Gemini]")
gem_result = call_gemini(system_prompt, user_prompt, gemini_key)
print(gem_result.text)
print(f"\n[エラー: {gem_result.error}]" if gem_result.error else "")
