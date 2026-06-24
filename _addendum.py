addendum = """

## 補足（ゲート①指摘対応 2026-06-12）

### CostGuard月次リセット
- get_costs() は datetime.now(JST).replace(day=1) を月始としてカウント
- 月初00:00を跨いだ瞬間に自動リセット（cost_log.jsonl のタイムスタンプベース）
- 手動再開不要

### pending_tasks 空の動作
- スキャン結果0件 → ログに「No pending tasks」出力して正常終了 (exit 0)
- LINE通知なし（毎5分の沈黙通知を避ける）

### タイムアウト時の挙動
- Claude Code が 1500秒超 → subprocess.run.TimeoutExpired
- ハンドラ: exit_code=-1 として扱い、gate_runner.handle_ng("TIMEOUT") 経由で再投入
- 試行2回でタイムアウトが続けば blocked_tasks/ に移動 + LINE

### --dangerously-skip-permissions のリスク軽減
- --add-dir でses_work配下に限定
- Claude Code は ANTHROPIC_API_KEY で認証（ローカルファイルアクセスのみ）
- 実行プロンプトには「ses_work外への書き込み禁止」をシステムプロンプトで明示

### blocked_tasks/ の確認プロセス
- LINE通知に blocked_tasks/ のフルパスを記載
- ジョブズは毎チャット開始時に blocked_tasks/ をスキャンし、新規があれば即座に松野へ報告
- 松野判断後、ジョブズが pending_tasks/ へファイル名を __retry_manual 付きで戻す or 削除

### ロールバック手順
- done_tasks/ から pending_tasks/ への戻し: move コマンドで可能
- blocked_tasks/ から pending_tasks/ への戻し: 同上
- runner は新しいファイル名で再認識する（試行回数はリセットされる）

### テスト網羅性追加
- 単体テスト不要（ジョブズ判断: ROI低い）
- 統合テスト:
  1. pending_tasks/ 空状態での起動 → exit 0
  2. ダミー指示書1件 → 完走 → done_tasks/ 移動
  3. 故意に失敗する指示書（NG確定）→ blocked_tasks/ 移動
  4. CostGuard $140 強制超え（cost_log.jsonl を書き換え）→ abort + LINE
"""

with open("task_auto_runner/SPEC.md", "a", encoding="utf-8") as f:
    f.write(addendum)
print("SPEC.md addendum appended")
