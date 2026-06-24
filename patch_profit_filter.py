path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# run_matchingのsystemプロンプトに粗利フィルタ指示を追加
old = 'system = \'SES matching AI. Reply JSON only.\n{"candidates":'
new = 'system = \'SES matching AI. Reply JSON only.\nIMPORTANT: Only include candidates where (project_price - candidate_price) >= 5. Minimum gross profit is 5万円. Exclude candidates whose price exceeds project price or leaves less than 5万円 gross profit.\n{"candidates":'

content = content.replace(old, new, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("done")
