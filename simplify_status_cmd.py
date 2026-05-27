
import sys, io, re, requests
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py"
with open(path, encoding='utf-8') as f:
    content = f.read()

# 1. update_candidate_status と find_project_by_keyword を改良版に置換
old_funcs_marker = "def update_candidate_status(page_id, candidate_name, new_status):"
new_funcs = '''
# ── ステータス略語マッピング ──────────────────────────────────────
STATUS_ALIASES = {
    "前": "意向確認前",
    "確認": "意向確認中", "確認中": "意向確認中", "いこう": "意向確認中",
    "面談": "面談希望", "面談希望": "面談希望", "希望": "面談希望",
    "調整": "面談調整中", "調整中": "面談調整中",
    "済": "面談済み", "面談済": "面談済み", "済み": "面談済み",
    "合格": "合格", "ok": "合格", "OK": "合格", "〇": "合格",
    "ng": "NG", "NG": "NG", "×": "NG", "ばつ": "NG",
}

def normalize_status(raw):
    """略語をステータス正式名に変換"""
    return STATUS_ALIASES.get(raw.strip(), raw.strip())

def normalize_candidate_name(raw):
    """イニシャル・略称を正規化（ドット・スペース除去・大文字化）"""
    return raw.replace(".", "").replace(" ", "").replace("　", "").upper()

def find_candidate_in_text(text, name_query):
    """案件詳細テキストから候補者行を探す（部分一致）"""
    nq = normalize_candidate_name(name_query)
    for line in text.split("\\n"):
        if "▶" not in line:
            continue
        # 行から候補者名部分を抽出（番号と単価の間）
        m = re.search(r"\\d+\\.\\s+(.+?)\\s+/", line)
        if m:
            cname = m.group(1).strip()
            if nq in normalize_candidate_name(cname):
                return line, cname
    return None, None

def update_candidate_status(page_id, candidate_name, new_status):
    """案件詳細の候補者ステータスを更新する"""
    r = requests.get(f"https://api.notion.com/v1/pages/{page_id}",
                     headers=NOTION_HEADERS, timeout=10)
    if r.status_code != 200:
        return False, f"案件取得失敗: {r.status_code}"

    props = r.json().get("properties", {})
    existing_items = props.get("案件詳細", {}).get("rich_text", [])
    existing_text = existing_items[0].get("plain_text", "") if existing_items else ""

    if not existing_text or "【候補者ステータス" not in existing_text:
        return False, "候補者ステータス欄が見つかりません"

    matched_line, matched_name = find_candidate_in_text(existing_text, candidate_name)
    if not matched_line:
        return False, f"「{candidate_name}」が見つかりません"

    new_line = re.sub(r"▶ .+$", f"▶ {new_status}", matched_line)
    updated_text = existing_text.replace(matched_line, new_line)[:1900]

    r2 = requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=NOTION_HEADERS,
        json={"properties": {"案件詳細": {"rich_text": [{"type": "text", "text": {"content": updated_text}}]}}},
        timeout=10
    )
    if r2.status_code == 200:
        return True, matched_name
    return False, f"更新失敗: {r2.status_code}"


def find_projects_with_candidate(name_query):
    """候補者名で全案件を横断検索してヒットした(page_id, proj_name, matched_name)を返す"""
    pages = notion_query(NOTION_PROJECT_DB_ID, {
        "or": [
            {"property": "ステータス", "select": {"equals": "募集中"}},
            {"property": "ステータス", "select": {"equals": "稼働中"}},
            {"property": "ステータス", "select": {"equals": "選考中"}},
        ]
    })
    results = []
    for p in pages:
        props = p.get("properties", {})
        name_items = props.get("案件名", {}).get("title", [])
        proj_name = name_items[0].get("plain_text", "") if name_items else ""
        detail_items = props.get("案件詳細", {}).get("rich_text", [])
        detail_text = detail_items[0].get("plain_text", "") if detail_items else ""
        if "【候補者ステータス" not in detail_text:
            continue
        matched_line, matched_name = find_candidate_in_text(detail_text, name_query)
        if matched_line:
            results.append((p["id"], proj_name, matched_name))
    return results

'''

# 旧関数を新関数で置換
old_func_end = "def find_project_by_keyword(keyword):"
old_find_func = '''def find_project_by_keyword(keyword):
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

# 旧update_candidate_statusから旧find_project_by_keywordまでを新関数に置換
start_marker = "def update_candidate_status(page_id, candidate_name, new_status):"
end_marker = "\ndef build_matching_result_reply():"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx == -1 or end_idx == -1:
    print(f"マーカー見つからず start={start_idx} end={end_idx}")
    sys.exit(1)

content = content[:start_idx] + new_funcs + content[end_idx:]
print("関数置換OK")

# 2. ステータス更新コマンド処理を簡略版に置換
old_cmd = '''    # ── ステータス更新コマンド ─────────────────────────────────────
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

'''

new_cmd = '''    # ── ステータス更新コマンド（簡略版）──────────────────────────────
    # 書式: 「更新 候補者名 ステータス略語」
    # 例:  「更新 RH 確認中」「更新 MY 面談」「更新 OA NG」
    if text_stripped.startswith("更新 ") or text_stripped.startswith("更新　"):
        parts = text_stripped[2:].strip().split()
        if len(parts) < 2:
            reply_message(reply_token,
                "書式: 更新 候補者名 ステータス\\n"
                "例: 更新 RH 確認中 / 更新 MY 面談 / 更新 OA NG\\n"
                "ステータス略語: 前 確認 面談 調整 済 合格 OK NG",
                sender_token)
            return
        name_query = parts[0]
        status_raw = parts[1]
        new_status = normalize_status(status_raw)
        valid = list(STATUS_ALIASES.values()) + list(STATUS_ALIASES.keys())
        if new_status not in ["意向確認前","意向確認中","面談希望","面談調整中","面談済み","合格","NG"]:
            reply_message(reply_token,
                f"「{status_raw}」は無効です\\n略語: 前 確認 面談 調整 済 合格 OK NG",
                sender_token)
            return
        # 候補者名で案件を横断検索
        hits = find_projects_with_candidate(name_query)
        if not hits:
            reply_message(reply_token, f"「{name_query}」が候補者リストに見つかりません", sender_token)
            return
        if len(hits) > 1:
            # 複数案件にいる場合は一覧を返す → 「更新 RH 確認中 Java」で案件を絞れる案内
            names = "\\n".join(f"{i+1}. {n}（{m}）" for i, (_, n, m) in enumerate(hits[:5]))
            if len(parts) >= 3:
                # 3つ目の引数を案件キーワードとして絞り込み
                proj_kw = parts[2]
                filtered = [(pid, pn, mn) for pid, pn, mn in hits if proj_kw.lower() in pn.lower()]
                if len(filtered) == 1:
                    hits = filtered
                else:
                    reply_message(reply_token,
                        f"複数案件にヒット:\\n{names}\\n\\n絞り込み例: 更新 {name_query} {status_raw} Java",
                        sender_token)
                    return
            else:
                reply_message(reply_token,
                    f"「{name_query}」は複数案件に候補中:\\n{names}\\n\\n案件を絞る場合: 更新 {name_query} {status_raw} 案件キーワード\\n全件更新する場合: 更新 {name_query} {status_raw} 全部",
                    sender_token)
                return
        if len(parts) >= 3 and parts[2] == "全部":
            # 全案件一括更新
            success_list = []
            for pid, pn, mn in hits:
                ok, result = update_candidate_status(pid, mn, new_status)
                if ok:
                    success_list.append(pn[:20])
            reply_message(reply_token,
                f"✅ {len(success_list)}件更新\\nステータス: {new_status}\\n" + "\\n".join(success_list),
                sender_token)
            return
        page_id, proj_name, matched_name = hits[0]
        ok, result = update_candidate_status(page_id, matched_name, new_status)
        if ok:
            reply_message(reply_token,
                f"✅ {matched_name} → {new_status}\\n{proj_name[:30]}",
                sender_token)
        else:
            reply_message(reply_token, f"❌ 更新失敗: {result}", sender_token)
        return

'''

if old_cmd in content:
    content = content.replace(old_cmd, new_cmd)
    print("コマンド置換OK")
else:
    print("旧コマンドが見つかりません")
    sys.exit(1)

# 構文チェック
import ast
try:
    ast.parse(content)
    print("構文チェックOK")
except SyntaxError as e:
    print(f"構文エラー: {e}")
    sys.exit(1)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("書き込み完了")
