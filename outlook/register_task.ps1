# Outlookメール自動チェック タスクスケジューラ登録
# PowerShellで管理者として実行してください

$pythonPath = "C:\Users\ma_py\AppData\Local\Programs\Python\Python312\python.exe"
$scriptPath = "C:\Users\ma_py\OneDrive\デスクトップ\ses_work\outlook\outlook_to_notion.py"
$taskName   = "SES_Outlook_To_Notion"

# 既存タスクを削除（上書き）
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

$action  = New-ScheduledTaskAction -Execute $pythonPath -Argument "`"$scriptPath`""
$trigger = New-ScheduledTaskTrigger -Daily -At "09:00"
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 1) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5)

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest -Force

Write-Host "✅ タスク登録完了！毎朝9時に自動実行されます。" -ForegroundColor Green
Write-Host ""
Write-Host "確認コマンド: Get-ScheduledTask -TaskName '$taskName'"
