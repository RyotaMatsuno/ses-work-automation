import os
import re
import shutil

SES = os.getcwd()  # C:\Users\ma_py\OneDrive\デスクトップ\ses_work
print(f"SES = {SES}")

# ============================================================
# Fix 1: notify_line.py - Notion fetch廃止
# ============================================================
path = os.path.join(SES, "matching_v2", "notify_line.py")
print(f"notify_line path: {path}")
print(f"exists: {os.path.exists(path)}")

shutil.copy(path, path + ".bak_0528")

with open(path, encoding="utf-8") as f:
    src = f.read()

# 担当者判定関数を追加
new_func = '''
def get_assignee_from_source(input_source):
    """Notion fetchなしでinput_sourceから担当者を判定"""
    if input_source and "岡本" in str(input_source):
        return "岡本"
    return "松野"

'''

src = src.replace("def get_assignee(page_id:", new_func + "def get_assignee(page_id:")

# main()内のnotion_headers生成を削除
src = src.replace(
    "    notion_headers = build_notion_headers()\n    line_accounts = None if args.dry_run else build_line_accounts()",
    "    line_accounts = None if args.dry_run else build_line_accounts()",
)

# project_assignee をNotion fetchからinput_source判定に
src = src.replace(
    "        project_assignee = get_assignee_cached(project_id, notion_headers, assignee_cache)",
    "        project_assignee = get_assignee_from_source(get_project_input_source(item))",
)

# engineer_assignee をNotion fetchからinput_source判定に
src = src.replace(
    "            engineer_assignee = get_assignee_cached(engineer_id, notion_headers, assignee_cache)",
    "            engineer_assignee = get_assignee_from_source(get_candidate_input_source(candidate))",
)

# get_page_info_cached をダミーに
old_cached = """def get_page_info_cached(page_id, headers, cache, page_type):
    key = (page_type, page_id)
    if key not in cache:
        cache[key] = get_page_info(page_id, headers, page_type)
    return dict(cache[key])"""

new_cached = """def get_page_info_cached(page_id, headers, cache, page_type):
    \"\"\"Notion fetchを廃止 - result.jsonの情報のみ使用\"\"\"
    return empty_page_info(page_type)"""

if old_cached in src:
    src = src.replace(old_cached, new_cached)
    print("get_page_info_cached replaced OK")
else:
    print("WARNING: get_page_info_cached not found exactly")

# project_info の notion_headers引数をNoneに
src = src.replace(
    '        project_info = get_page_info_cached(project_id, notion_headers, info_cache, "project")',
    '        project_info = get_page_info_cached(project_id, None, info_cache, "project")',
)
src = src.replace(
    '            engineer_info = get_page_info_cached(engineer_id, notion_headers, info_cache, "engineer")',
    '            engineer_info = get_page_info_cached(engineer_id, None, info_cache, "engineer")',
)

with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("notify_line.py patched OK")

# ============================================================
# Fix 2: webhook_server.py - 8766依存廃止
# ============================================================
path2 = os.path.join(SES, "line_webhook", "webhook_server.py")
print(f"webhook path: {path2}")
print(f"exists: {os.path.exists(path2)}")

shutil.copy(path2, path2 + ".bak_0528")

with open(path2, encoding="utf-8") as f:
    src2 = f.read()

# analyze_skill_sheet 関数を追加（handle_file_messageの直前）
new_func2 = '''
def analyze_skill_sheet(b64_data, mime_type):
    """Claude APIでスキルシートを直接解析（8766不要）"""
    if mime_type == "application/pdf":
        content = [
            {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": b64_data}},
            {"type": "text", "text": "このスキルシートから人材情報をJSONのみで抽出。マークダウン不要。\\n形式: {\\"name\\":\\"\\",\\"skills\\":[],\\"price\\":0,\\"available_date\\":\\"\\",\\"experience_years\\":0,\\"location\\":\\"\\",\\"affiliation\\":\\"\\",\\"note\\":\\"\\"}"}
        ]
    else:
        mt = mime_type if mime_type.startswith("image/") else "image/jpeg"
        content = [
            {"type": "image", "source": {"type": "base64", "media_type": mt, "data": b64_data}},
            {"type": "text", "text": "このスキルシートから人材情報をJSONのみで抽出。マークダウン不要。\\n形式: {\\"name\\":\\"\\",\\"skills\\":[],\\"price\\":0,\\"available_date\\":\\"\\",\\"experience_years\\":0,\\"location\\":\\"\\",\\"affiliation\\":\\"\\",\\"note\\":\\"\\"}"}
        ]
    system = "SES業界のスキルシート解析AI。JSON形式のみ返答。price=万円整数。experience_years=業界経験年数の整数。"
    res = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": "claude-opus-4-6", "max_tokens": 2000, "system": system, "messages": [{"role": "user", "content": content}]},
        timeout=60
    )
    if res.status_code == 200:
        try:
            text = res.json()["content"][0]["text"]
            return json.loads(re.sub(r\'```json|```\', \'\', text).strip())
        except Exception as e:
            print(f"[analyze_skill_sheet] parse error: {e}")
            return {}
    print(f"[analyze_skill_sheet] API error: {res.status_code}")
    return {}

'''

# handle_file_messageの前に挿入
insert_marker = "\ndef handle_file_message("
if insert_marker in src2:
    src2 = src2.replace(insert_marker, new_func2 + insert_marker)
    print("analyze_skill_sheet inserted OK")
else:
    print("ERROR: insertion point not found")

# handle_file_message本体をregexで置換
new_handle = '''def handle_file_message(message_id, mime_type, reply_token, sender, sender_token):
    """LINEから送られたPDF/画像ファイルをClaude APIで直接解析してNotion登録"""
    user_id = MATSUNO_USER_ID if sender == "matsuno" else OKAMOTO_USER_ID
    try:
        # 1. LINEからファイルコンテンツ取得
        token = MATSUNO_CHANNEL_TOKEN if sender == "matsuno" else OKAMOTO_CHANNEL_TOKEN
        res = requests.get(
            f"https://api-data.line.me/v2/bot/message/{message_id}/content",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30
        )
        if res.status_code != 200:
            reply_message(reply_token, f"❌ ファイル取得失敗: {res.status_code}", sender_token)
            return

        b64_data = base64.b64encode(res.content).decode()

        # 2. 解析中メッセージ
        reply_message(reply_token, "📋 スキルシート解析中...", sender_token)

        # 3. Claude APIで直接スキル抽出
        info = analyze_skill_sheet(b64_data, mime_type)
        if not info or not info.get("name"):
            push_message(user_id, "❌ スキル情報を抽出できませんでした。テキスト形式で再送してください。", sender_token)
            return

        name = info.get("name", "不明")

        # 4. Notion登録
        success, reason = register_engineer(info, str(info), sender, user_id=user_id)
        if not success:
            msg = f"📋 解析完了: {name}\\n\\n"
            if reason == "area_out_of_scope":
                msg += AREA_OUT_OF_SCOPE_REPLY
            elif reason == "foreign_nationality":
                msg += "外国籍のため登録をスキップしました"
            else:
                msg += f"⚠️ 登録スキップ: {reason}"
            push_message(user_id, msg, sender_token)
            return

        # 5. 逆マッチング
        active_projects = deduplicate_projects(get_active_projects())
        result_m = run_reverse_matching_full(info, active_projects)
        matches = result_m.get("matches", [])[:3]

        if MATCHING_LOGIC_AVAILABLE:
            msg = build_reverse_match_message_v2(
                name, matches, normalize_price(info.get("price", 0)) or 0)
        else:
            msg = build_reverse_match_message(name, matches)

        push_message(user_id, msg, sender_token)

    except Exception as e:
        push_message(user_id, f"❌ スキルシート処理エラー: {str(e)[:200]}", sender_token)
        traceback.print_exc()'''

# 関数全体をregexで置換
pattern = r"def handle_file_message\(message_id.*?(?=\ndef [a-z_]|\Z)"
match = re.search(pattern, src2, re.DOTALL)
if match:
    src2 = src2[: match.start()] + new_handle + "\n\n\n" + src2[match.end() :]
    print("handle_file_message replaced OK")
else:
    print("ERROR: handle_file_message not found")

with open(path2, "w", encoding="utf-8") as f:
    f.write(src2)

print("webhook_server.py patched OK")
print("=== ALL DONE ===")
