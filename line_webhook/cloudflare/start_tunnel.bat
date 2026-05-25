@echo off
chcp 65001 > nul
cd /d "%~dp0"
cloudflared tunnel --config config.yml run jobz-command
