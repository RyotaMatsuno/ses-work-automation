# Phase 1: Global Kill-Switch Overhaul - Codex作業ルール

## 編集対象ファイル
- `cost_guard.py`（ses_workルート直下、1ファイルのみ）

## 禁止事項
- cost_guard.py以外のファイルを変更しない
- ロジックを勝手に追加しない（SPEC.mdの仕様のみ実装する）
- 既存の`get_costs()`・`send_line()`関数は変更しない

## 必須手順
1. 作業前にバックアップ: cost_guard.py → cost_guard.py.bak_phase1
2. SPEC.mdの仕様通りに実装
3. TASKS.mdのチェックリストを順番に消化し、完了したら[x]に更新
4. 最後に `python -c "import py_compile; py_compile.compile('cost_guard.py'); print('syntax_ok')"` で構文確認

## 注意
- schtasks コマンドはTASKS.mdのチェック項目に含めない（スケジューラ変更はジョブズが別途実行）
- gcloudコマンドはPATHに存在する想定で実装すること
