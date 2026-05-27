@echo off
cd /d "C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
set CODEX_CMD=C:\Users\ma_py\AppData\Roaming\npm\codex.cmd
%CODEX_CMD% --dangerously-bypass-approvals-and-sandbox -C propose_pipeline "SPEC.mdを読んでTASKS.mdの順番でpropose.pyを実装してください。DRY_RUN環境変数が1のときはIMAP接続せずコンソール出力のみとすること。" >> propose_pipeline\codex_propose.log 2>&1
