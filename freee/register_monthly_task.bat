@echo off
REM Run AFTER freee_invoice_monthly.py exists (post-Codex). Registers monthly draft task.
schtasks /Create /TN "TERRA_Monthly_Invoice" /TR "\"%~dp0run_monthly_invoice.bat\"" /SC MONTHLY /D 1 /ST 09:30 /RL LIMITED /F
schtasks /Query /TN "TERRA_Monthly_Invoice"
