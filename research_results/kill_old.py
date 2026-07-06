import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import subprocess

# Kill old process
subprocess.run(["taskkill", "/PID", "33516", "/F"], capture_output=True)
print("Old process killed")
