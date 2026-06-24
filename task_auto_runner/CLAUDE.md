# CLAUDE.md - task_auto_runner
最終更新: 2026-06-12

## 作業ルール
- 実装者は Claude Code CLI (Sonnet 4.6)
- 3点セット必須参照: SPEC.md / TASKS.md / 本ファイル
- 全Pythonスクリプト冒頭に sys.stdout.reconfigure(encoding='utf-8', errors='replace')

## 重要な制約
- jobz-command の27分制限 → Claude Code側は --max-budget-usd と timeout=1500 で抑制
- 月次CostGuard: cost_guard.py の get_costs() を必ず使う（重複実装禁止）
- LINE通知: daily_report.py の push_message() を再利用（urllib版に書き換えてもよい）

## 環境変数（config/.env）
- ANTHROPIC_API_KEY: Claude Code CLI が認証に使う（既存）
- LINE_CHANNEL_ACCESS_TOKEN: LINE Messaging API
- 松野 user_id: Ue3508b43b84991f5a68281da5bf4cf39

## ディレクトリ規約
- pending_tasks/ : 未処理（runner 消化対象）
- running_tasks/ : 実行中ログ・JSON
- done_tasks/ : 成功完了
- blocked_tasks/ : 連続失敗・人間確認待ち
- 全て ses_work/ 直下

## 試行回数管理
- ファイル名末尾に __try{N} を付与
- 初回: ファイル名そのまま（試行0回扱い）
- 再投入: <original>__try1.md, __try2.md, ...
- N>=2 で blocked_tasks/ 強制移動

## ロックファイル
- task_auto_runner/logs/runner.lock
- PID書き込み → 起動時に存在チェック
- psutilでプロセス生存確認、死んでいれば古いロックは削除

## subprocess呼び出し時の注意（Windows）
- shell=False が安全
- 日本語パスはosモジュールで取得
- Claude Code CLI は cmd経由: ['claude.cmd', '-p', ...] または 'claude' で直接

## ゲート② 連携
- python gate_checker/gate_check.py --phase implementation --file <target>
- exit 0=GO, 1=NG, 2=エラー/スキップ
- results/gate_implementation_YYYYMMDD_HHMMSS.json に結果保存
- runnerは標準出力から最終verdictを正規表現で抽出

## 禁止事項
- 1指示書あたり $5 を超える呼び出し（--max-budget-usd 強制）
- ロックなしの起動
- exception を握りつぶす（必ずログかLINE通知）
- pending_tasks/ 以外のディレクトリのファイルを実行

## 完了条件
1. python task_auto_runner/runner.py --dry-run が正常終了
2. テスト指示書を pending_tasks/ に置いて実走 → done_tasks/ 移動 + LINE通知
3. schtasks 登録完了
