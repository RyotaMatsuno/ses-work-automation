import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

os.makedirs("task_auto_runner", exist_ok=True)

spec = """# task_auto_runner SPEC.md
最終更新: 2026-06-12

## 目的
ジョブズが pending_tasks/ に保存した【Cursor作業指示】を Claude Code CLI で自動実行し、
完了後にゲート②自動レビュー → LINE通知まで一気通貫で行う「松野手作業ゼロ」基盤。

## 全体フロー
```
ジョブズ → pending_tasks/xxx.md 保存
        ↓
task_auto_runner/runner.py（5分おき起動）
        ↓
1) pending_tasks/ をスキャン（古い順）
2) lockファイル取得（多重起動防止）
3) CostGuard チェック（月次$140超なら全スキップ）
4) 各ファイルを順次実行:
   a) Claude Code CLI 起動
      claude -p "$(cat <file>)" \\
             --dangerously-skip-permissions \\
             --model sonnet \\
             --max-budget-usd 5 \\
             --output-format json \\
             --no-session-persistence
   b) 終了コードと出力JSONを running_tasks/<basename>.json に保存
   c) ゲート②自動実行（gate_check.py --phase implementation）
   d) GO → done_tasks/ 移動 + LINE通知（成功）
      NG（1回目）→ 再投入（pending_tasks/ に戻す + 試行回数++）
      NG（2回目）→ blocked_tasks/ 移動 + LINE通知（人間確認要）
5) lock解放
```

## ディレクトリ構成
```
ses_work/
├── pending_tasks/        # 既存。ジョブズが保存・runnerが消化
├── running_tasks/        # 新設。実行中の作業ログ・JSON出力先
├── done_tasks/           # 新設。完了済み（成功）の保管
├── blocked_tasks/        # 新設。失敗で人間確認待ち
└── task_auto_runner/
    ├── SPEC.md
    ├── TASKS.md
    ├── CLAUDE.md
    ├── runner.py         # メインループ
    ├── claude_invoker.py # Claude Code CLI ラッパ
    ├── gate_runner.py    # ゲート②呼び出し + 再投入ロジック
    ├── notifier.py       # LINE通知（既存push_message流用）
    ├── logs/             # 実行ログ
    └── run_auto_runner.bat # タスクスケジューラ起動用
```

## ファイル名規約
- pending_tasks/YYYYMMDD_HHMMSS_<topic>.md
- 試行回数を埋め込む形式: YYYYMMDD_HHMMSS_<topic>__try<N>.md
- N>=2 で blocked_tasks/ 行き判定

## CostGuard
- 既存 cost_guard.py の get_costs() を流用
- 月次$140超 → runner自体が起動時にabort + LINE通知1回
- 1指示書あたり Claude Code の --max-budget-usd 5 で制限

## Claude Code CLI 呼び出し詳細
```
claude -p "<指示書本文>" \\
       --dangerously-skip-permissions \\
       --model sonnet \\
       --max-budget-usd 5 \\
       --output-format json \\
       --no-session-persistence \\
       --add-dir <ses_work絶対パス>
```
- 標準出力: JSON形式の最終応答（最後の行）
- exit code: 0=成功, 非0=失敗
- タイムアウト: subprocess.run(timeout=1500)（25分上限。jobz-command 27分制限内）

## ゲート② 対象ファイル特定ロジック
指示書本文を正規表現で解析:
- 「対象ディレクトリ:」または「対象ファイル:」の行を抽出
- ディレクトリの場合は、その配下で直近変更されたファイル（git diff）を対象に
- 見つからない場合は SPEC.md があればそれを対象

## LINE通知文言
### 成功
```
✅ [auto_runner] {filename} 完了
判定: GO
コスト: ${cost}
所要時間: {duration}秒
```
### NG（再投入）
```
🔄 [auto_runner] {filename} NG → 再投入（{try}/2回目）
NG理由: {reason}
```
### 失敗（blocked）
```
🚫 [auto_runner] {filename} 2回連続NG → 人間確認要
NG理由: {reason}
場所: blocked_tasks/{filename}
```
### CostGuard発動
```
⛔ [auto_runner] 月次コスト$140超 → 全作業停止
今月コスト: ${monthly}
```

## 二重起動防止
- task_auto_runner/logs/runner.lock にPID書き込み
- 起動時にPID存在確認 → 生きていればexit
- 終了時に必ず削除（try/finally）

## 起動方式
- Windowsタスクスケジューラ: 5分おき
- weekday_guard.py 不要（土日も走らせる方が事故時の検知が早い）

## 動作確認コマンド
```
python task_auto_runner/runner.py --dry-run
→ pending_tasks/ をスキャンするだけで実行はしない
```

## ジョブズへの確認義務
- blocked_tasks/ に新規ファイルが入った場合、次のチャットでジョブズに確認を促す
- LINE通知だけだと松野が見落とすため、ジョブズ自身もチェックする
"""

with open("task_auto_runner/SPEC.md", "w", encoding="utf-8") as f:
    f.write(spec)
print("SPEC.md written:", os.path.getsize("task_auto_runner/SPEC.md"), "bytes")
