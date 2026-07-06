import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
print("CWD:", os.getcwd())
print("Files in CWD:", os.listdir('.'))
