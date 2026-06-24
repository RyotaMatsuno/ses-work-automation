# Task AO: 5分おきに realtime_match_worker を実行する
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $Python) { $Python = "python" }
Set-Location $Root
& $Python matching_v3\worker\realtime_match_worker.py
