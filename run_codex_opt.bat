@echo off
cd /d C:\Users\ma_py\OneDrive\Desktop\ses_work\mail_pipeline
set PROMPT_TEXT=SPEC_opt.mdとCLAUDE_opt.mdを読んでTASKS_opt.mdの順番でmail_pipeline.pyを改修してください。
call C:\Users\ma_py\AppData\Roaming\npm\codex.cmd --dangerously-bypass-approvals-and-sandbox "%PROMPT_TEXT%" > ..\codex_pipeline_opt.log 2>&1
