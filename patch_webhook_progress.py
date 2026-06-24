import sys

sys.stdout.reconfigure(encoding="utf-8")

# webhook_server.pyに「進捗」コマンドを直接追加
wh_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py"
with open(wh_path, encoding="utf-8") as f:
    content = f.read()

# 「マッチング」コマンドの直後に「進捗」コマンドを挿入
target = """    # マッチング結果照会
    if "マッチング" in text_stripped and len(text_stripped) <= 10:
        matching_reply = build_matching_result_reply()
        chunks = split_line_message(matching_reply)
        reply_message(reply_token, chunks[0], sender_token)
        push_user_id = user_id or (MATSUNO_USER_ID if sender == "matsuno" else OKAMOTO_USER_ID)
        for chunk in chunks[1:]:
            push_message(push_user_id, chunk, sender_token)
        return"""

progress_cmd = """
    # 案件進捗照会
    if "進捗" in text_stripped and len(text_stripped) <= 6:
        progress_reply = build_progress_reply()
        chunks = split_line_message(progress_reply)
        reply_message(reply_token, chunks[0], sender_token)
        push_user_id = user_id or (MATSUNO_USER_ID if sender == "matsuno" else OKAMOTO_USER_ID)
        for chunk in chunks[1:]:
            push_message(push_user_id, chunk, sender_token)
        return"""

insert_after = """        return"""

# targetブロックの後に挿入
if target in content and progress_cmd not in content:
    content = content.replace(target, target + "\n" + progress_cmd, 1)
    print("進捗コマンド挿入OK")
else:
    if progress_cmd in content:
        print("既に挿入済み")
    else:
        print("挿入対象が見つからない")
        print(content[content.find("マッチング") : content.find("マッチング") + 300])

# build_progress_reply関数を追加（build_matching_result_replyの直後）
progress_func = '''

def build_progress_reply():
    """案件進捗をReply API用にフォーマット"""
    from datetime import datetime
    try:
        pages = notion_query(NOTION_PROJECT_DB_ID, {
            "or": [
                {"property": "ステータス", "select": {"equals": "募集中"}},
                {"property": "ステータス", "select": {"equals": "選考中"}},
            ]
        })
    except Exception as e:
        print(f"[progress] notion error: {e}")
        return "【案件進捗】\\nデータ取得失敗"

    weekdays = ["月","火","水","木","金","土","日"]
    now = datetime.now()
    header = f"【案件進捗】{now.strftime('%m/%d')}（{weekdays[now.weekday()]}）"
    lines = [header, ""]

    action_lines = []
    has_project = False

    for p in pages:
        props = p.get("properties", {})
        name_items = props.get("案件名", {}).get("title", [])
        name = name_items[0].get("plain_text", "（名称なし）") if name_items else "（名称なし）"
        price = props.get("単価（万円）", {}).get("number")
        price_str = f"{price}万" if price else "-万"

        teian    = props.get("提案中",   {}).get("number") or 0
        mendan   = props.get("面談希望", {}).get("number") or 0
        ng       = props.get("NG",       {}).get("number") or 0
        goukaku  = props.get("合格",     {}).get("number") or 0
        seiyaku  = props.get("成約",     {}).get("number") or 0

        # 全部0の案件は省略
        if not any([teian, mendan, ng, goukaku, seiyaku]):
            continue

        has_project = True
        lines.append(f"■ {name}（{price_str}）")
        row = f"  提案中:{teian} / 面談希望:{mendan} / NG:{ng} / 合格:{goukaku}"
        if seiyaku:
            row += f" / 成約:{seiyaku}"
        lines.append(row)
        lines.append("")

        if mendan > 0:
            action_lines.append(f"  {name} → 面談希望{mendan}件")

    if not has_project:
        lines.append("進行中案件なし（提案・面談希望ともに0）")
    
    if action_lines:
        lines.append("⚡ 要アクション")
        lines.extend(action_lines)

    return "\\n".join(lines)
'''

# build_matching_result_reply関数の直後に追加
insert_after_func = "def build_matching_result_reply():"
idx = content.rfind(insert_after_func)
if idx >= 0 and "def build_progress_reply" not in content:
    # 関数末尾を探す（次のdef行を探す）
    next_def = content.find("\ndef ", idx + 1)
    if next_def >= 0:
        content = content[:next_def] + progress_func + content[next_def:]
        print("build_progress_reply追加OK")
    else:
        content += progress_func
        print("build_progress_reply末尾追加OK")
elif "def build_progress_reply" in content:
    print("build_progress_reply既に存在")
else:
    print("挿入位置が見つからない")

with open(wh_path, "w", encoding="utf-8") as f:
    f.write(content)
print("webhook_server.py更新完了")
