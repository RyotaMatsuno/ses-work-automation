# -*- coding: utf-8 -*-
# 変更2: _extract_contacts 関数と detail_query 関数を追加
# + handle_line_query に「詳細 N」パターン検出を追加

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

# _limit_reply の直前に新関数2つを挿入
insert_before = "def _limit_reply(lines: list[str], items: list, formatter, header_page: dict) -> str:"

new_funcs = '''
# ── 連絡先抽出（一覧表示用） ───────────────────────────────────────
def _extract_contacts(text: str) -> str:
    """案件詳細テキストからメアド・電話・担当者名を抽出して返す"""
    if not text:
        return ""
    import re as _re
    _EMAIL_RE = _re.compile(r'[a-zA-Z0-9._%+\\-]+@[a-zA-Z0-9.\\-]+\\.[a-zA-Z]{2,}')
    _PHONE_RE = _re.compile(r'0[0-9]{1,4}[\\-\\s]?[0-9]{3,4}[\\-\\s]?[0-9]{4}')
    _CTCT_RE  = _re.compile(r'^担当[^者が]{0,3}[：:]\\s*\\S')
    contacts: list[str] = []
    _SKIP = ("送信者:", "件名:", "Subject:", "From:", "[LINE auto-register")
    for _ln in text.split("\\n"):
        _s = _ln.strip()
        if not _s:
            continue
        if any(_s.startswith(_p) for _p in _SKIP):
            continue
        if _CTCT_RE.match(_s) and len(_s) < 25 and _s not in contacts:
            contacts.append(_s)
        _em = _EMAIL_RE.search(_s)
        if _em and _em.group(0) not in contacts:
            contacts.append(_em.group(0))
        _ph = _PHONE_RE.search(_s)
        if _ph and len(_s) <= 20 and _ph.group(0) not in contacts:
            contacts.append(_ph.group(0))
        if len(contacts) >= 4:
            break
    return " / ".join(contacts)


# ── 詳細照会（「詳細 ①」コマンド用） ─────────────────────────────
# 番号→インデックスのマッピング
_NUM_MAP = {
    "①": 0, "②": 1, "③": 2, "④": 3, "⑤": 4,
    "⑥": 5, "⑦": 6, "⑧": 7, "⑨": 8, "⑩": 9,
    "1": 0, "2": 1, "3": 2, "4": 3, "5": 4,
    "6": 5, "7": 6, "8": 7, "9": 8, "10": 9,
    "11": 10, "12": 11, "13": 12, "14": 13, "15": 14,
    "16": 15, "17": 16, "18": 17, "19": 18, "20": 19,
    "21": 20, "22": 21, "23": 22, "24": 23, "25": 24,
    "26": 25, "27": 26, "28": 27, "29": 28, "30": 29,
    "31": 30,
}

# 直近の照会結果をキャッシュ（メモリ内・セッション限定）
_LAST_RESULTS: dict[str, list[dict]] = {}  # key: initial_station → projects list

def detail_query(text: str) -> str | None:
    """「詳細 ①」「詳細 6」などのコマンドを処理して案件全文を返す"""
    import re as _re
    # パターン: 詳細[スペース]番号
    m = _re.match(r'^詳細\\s*([①-⑩\\d]+)$', text.strip())
    if not m:
        return None
    num_str = m.group(1).strip()
    idx = _NUM_MAP.get(num_str)
    if idx is None:
        return f"「{num_str}」は無効な番号です。①〜⑩または1〜31で指定してください。"

    # キャッシュから取得
    if not _LAST_RESULTS:
        return "先に「イニシャル 駅名」で照会してから「詳細 番号」を送ってください。"

    # 最後の照会結果を使用
    last_key = list(_LAST_RESULTS.keys())[-1]
    projects = _LAST_RESULTS[last_key]

    if idx >= len(projects):
        return f"番号 {num_str} の案件はありません（全{len(projects)}件）。"

    pj = projects[idx]
    pj_name  = _text_prop(pj, PROP_PJNAME)
    req_sk   = _join(_multi_select_prop(pj, PROP_REQSK))
    opt_sk   = _join(_multi_select_prop(pj, PROP_OPTSK))
    loc      = _text_prop(pj, PROP_LOCATION)
    remote   = _select_prop(pj, PROP_REMOTE)
    period   = _text_prop(pj, PROP_PERIOD)
    budget   = _number_prop(pj, PROP_RATE)
    age      = business_days_since(pj.get("last_edited_time"))
    assignee = _select_prop(pj, PROP_ASSIGNEE)
    detail   = _text_prop(pj, PROP_PJDETAIL)

    lines = [
        f"【詳細 {num_str}】{pj_name}",
        f"必須: {req_sk}" + (f" / 尚可: {opt_sk}" if opt_sk else ""),
        f"単価: {_format_number(budget)}万" + (f" / {assignee}担当" if assignee else ""),
        f"勤務地: {loc}" + (f" ({remote})" if remote else "") + (f" / {period}" if period else "") + f" [{age}日前]",
        "",
        "【案件詳細全文】",
        detail if detail else "（詳細なし）",
    ]
    return "\\n".join(lines)


'''

if insert_before in content:
    content = content.replace(insert_before, new_funcs + insert_before)
    print("変更2 新関数挿入 OK", flush=True)
else:
    print("変更2 MISS", flush=True)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("変更2 書き込み完了", flush=True)
