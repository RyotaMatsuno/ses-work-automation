import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

# process_message内の「# マッチング結果照会」の直前に挿入
# 挿入する関数とコマンド処理を追加

new_functions = '''
def update_candidate_status(page_id, candidate_name, new_status):
    """案件詳細の候補者ステータスを更新する"""
    from dotenv import dotenv_values
    cfg = dotenv_values(ENV_PATH) if os.path.exists(ENV_PATH) else {}

    r = requests.get(f"https://api.notion.com/v1/pages/{page_id}",
                     headers=NOTION_HEADERS, timeout=10)
    if r.status_code != 200:
        return False, f"案件取得失敗: {r.status_code}"

    props = r.json().get("properties", {})
    existing_items = props.get("案件詳細", {}).get("rich_text", [])
    existing_text = existing_items[0].get("plain_text", "") if existing_items else ""

    if not existing_text or "【候補者ステータス" not in existing_text:
        return False, "候補者ステータス欄が見つかりません"

    # 候補者名を含む行のステータスを更新
    lines = existing_text.split("\\n")
    updated_lines = []
    found = False
    for line in lines:
        if candidate_name in line and "▶" in line:
            line = re.sub(r"▶ .+$", f"▶ {new_status}", line)
            found = True
        updated_lines.append(line)

    if not found:
        return False, f"「{candidate_name}」が見つかりません"

    updated_text = "\\n".join(updated_lines)[:1900]

    r2 = requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=NOTION_HEADERS,
        json={"properties": {"案件詳細": {"rich_text": [{"type": "text", "text": {"content": updated_text}}]}}},
        timeout=10
    )
    if r2.status_code == 200:
        return True, ""
    return False, f"更新失敗: {r2.status_code}"


def find_project_by_keyword(keyword):
    """キーワードで案件DBを検索してpage_idと案件名を返す"""
    pages = notion_query(NOTION_PROJECT_DB_ID, {
        "or": [
            {"property": "ステータス", "select": {"equals": "募集中"}},
            {"property": "ステータス", "select": {"equals": "稼働中"}},
            {"property": "ステータス", "select": {"equals": "選考中"}},
        ]
    })
    keyword_lower = keyword.lower()
    matches = []
    for p in pages:
        name_items = p.get("properties", {}).get("案件名", {}).get("title", [])
        name = name_items[0].get("plain_text", "") if name_items else ""
        if keyword_lower in name.lower():
            matches.append((p["id"], name))
    return matches

'''

# 既存のbuild_matching_result_reply関数の直前に挿入
insert_before = "def build_matching_result_reply():"
if insert_before in content:
    content = content.replace(insert_before, new_functions + insert_before)
    print("関数追加OK")
else:
    print("挿入位置が見つかりません")
    sys.exit(1)

# process_message内の「# マッチング結果照会」の前にステータス更新コマンドを追加
status_command = """
    # ── ステータス更新コマンド ─────────────────────────────────────
    # 書式: 「ステータス更新 案件キーワード / 候補者名 / 新ステータス」
    # 例:  「ステータス更新 Java基本設計 / R.H / 意向確認中」
    VALID_STATUSES = ["意向確認前", "意向確認中", "面談希望", "面談調整中", "面談済み", "合格", "NG"]
    if text_stripped.startswith("ステータス更新"):
        parts = text_stripped.replace("ステータス更新", "").strip().split("/")
        if len(parts) < 3:
            reply_message(reply_token,
                "書式: ステータス更新 案件キーワード / 候補者名 / 新ステータス\\n"
                f"ステータス一覧: {' | '.join(VALID_STATUSES)}",
                sender_token)
            return
        proj_kw = parts[0].strip()
        cand_name = parts[1].strip()
        new_status = parts[2].strip()
        if new_status not in VALID_STATUSES:
            reply_message(reply_token,
                f"ステータス「{new_status}」は無効です\\n"
                f"有効: {' | '.join(VALID_STATUSES)}",
                sender_token)
            return
        matches = find_project_by_keyword(proj_kw)
        if not matches:
            reply_message(reply_token, f"案件「{proj_kw}」が見つかりません", sender_token)
            return
        if len(matches) > 1:
            names = "\\n".join(f"{i+1}. {n}" for i, (_, n) in enumerate(matches[:5]))
            reply_message(reply_token,
                f"案件が複数ヒットしました。キーワードを絞ってください:\\n{names}",
                sender_token)
            return
        page_id, proj_name = matches[0]
        ok, err = update_candidate_status(page_id, cand_name, new_status)
        if ok:
            reply_message(reply_token,
                f"✅ 更新完了\\n案件: {proj_name}\\n候補者: {cand_name}\\nステータス: {new_status}",
                sender_token)
        else:
            reply_message(reply_token, f"❌ 更新失敗: {err}", sender_token)
        return

"""

# 「# マッチング結果照会」の前に挿入
insert_before2 = "    # マッチング結果照会"
if insert_before2 in content:
    content = content.replace(insert_before2, status_command + insert_before2)
    print("コマンド追加OK")
else:
    print("挿入位置2が見つかりません")
    sys.exit(1)

# 構文チェック
import ast

try:
    ast.parse(content)
    print("構文チェックOK")
except SyntaxError as e:
    print(f"構文エラー: {e}")
    sys.exit(1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("書き込み完了")
