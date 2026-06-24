path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# process_message内のマッチング結果取得後に粗利フィルタを追加
old = """        engineers = get_available_engineers()
        matching = run_matching(info, engineers)
        candidates = matching.get("candidates", [])"""

new = """        engineers = get_available_engineers()
        matching = run_matching(info, engineers)
        candidates = matching.get("candidates", [])
        # 粗利フィルタ: 案件単価 - 人材単価 >= 5万円
        project_price = normalize_price(info.get("price", 0)) or 0
        if project_price > 0:
            def gross_ok(c):
                cp = normalize_price(c.get("price", 0)) or 0
                if cp == 0: return True  # 単価不明は通す
                return (project_price - cp) >= 5
            filtered = [c for c in candidates if gross_ok(c)]
            ng_count = len(candidates) - len(filtered)
            if ng_count > 0:
                print(f"[profit_filter] {ng_count}名を粗利不足で除外")
            candidates = filtered"""

content = content.replace(old, new, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("done")
