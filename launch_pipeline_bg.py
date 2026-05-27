# -*- coding: utf-8 -*-
import subprocess, sys, os, time

proc = subprocess.Popen(
    [sys.executable, '-m', 'mail_pipeline.mail_pipeline'],
    cwd=r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work',
    stdout=open(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pipeline_run_now.log', 'w', encoding='utf-8'),
    stderr=subprocess.STDOUT,
    creationflags=0x00000008  # DETACHED_PROCESS
)
print(f'PID: {proc.pid}')
