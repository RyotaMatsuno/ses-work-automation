# Task AO: 5分おきに realtime_match_worker を実行するタスクを登録
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $Python) { $Python = "python" }
$Script = Join-Path $Root "matching_v3\worker\realtime_match_worker.py"
$TaskName = "SES_RealtimeMatch"
$Action = "`"$Python`" `"$Script`""
schtasks /Create /TN $TaskName /TR $Action /SC MINUTE /MO 5 /RU $env:USERNAME /F
Write-Host "Registered: $TaskName (every 5 minutes)"
