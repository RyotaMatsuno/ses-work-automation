@echo off
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
python freee\freee_invoice_v2.py --execute >> freee\monthly_invoice.log 2>&1
