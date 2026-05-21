import re

path = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old = "system = 'SES business message classifier. Reply JSON only.\\n\\nengineer:"
new = "system = 'SES business message classifier. Reply JSON only.\\nIMPORTANT: price field must be in 万円 unit as integer. e.g. \"65万\" or \"65万円\" -> 65, \"70万\" -> 70, \"650,000円\" -> 65. Never use raw yen values.\\n\\nengineer:"

content = content.replace(old, new, 1)
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("done")
