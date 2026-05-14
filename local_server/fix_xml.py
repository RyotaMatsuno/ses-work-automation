import os

xml_content = '''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>jobz-command server watchdog - auto restart every 5 min</Description>
  </RegistrationInfo>
  <Triggers>
    <TimeTrigger>
      <Repetition>
        <Interval>PT5M</Interval>
        <Duration>P9999D</Duration>
        <StopAtDurationEnd>false</StopAtDurationEnd>
      </Repetition>
      <StartBoundary>2026-01-01T00:00:00</StartBoundary>
      <Enabled>true</Enabled>
    </TimeTrigger>
    <LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBattery>false</DisallowStartIfOnBattery>
    <StopIfGoingOnBattery>false</StopIfGoingOnBattery>
    <ExecutionTimeLimit>PT1M</ExecutionTimeLimit>
    <Enabled>true</Enabled>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>python</Command>
      <Arguments>"C:\\Users\\ma_py\\OneDrive\\\\u30c7\\u30b9\\u30af\\u30c8\\u30c3\\u30d7\\ses_work\\local_server\\watchdog.py"</Arguments>
    </Exec>
  </Actions>
</Task>'''

# Write as UTF-16 LE with BOM (what schtasks expects)
xml_path = os.path.join(os.path.dirname(__file__), "jobz_watchdog_task.xml")
with open(xml_path, 'w', encoding='utf-16') as f:
    f.write(xml_content)

print(f"Written UTF-16 BOM to {xml_path}")
