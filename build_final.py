import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ② の問題: CONTENT_MARKERSで "◆ スキル" が "◆ 案件名" より先にヒットしている
# → CONTENT_MARKERSの順序を「案件名」>「業務内容」>「スキル」に変更
# また "◆ 案件名" で始まるテキストは案件名だけでなくその後の業務内容も含む → OK

# 新バージョンのCONTENT_MARKERSの順序:
# 1. 業務内容系 (最優先)
# 2. 案件名/概要系
# 3. スキル系 (最後)

paths = [
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py",
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py",
]

# 新しい _clean_detail の完全版（Unicodeエスケープ使用）
NEW_CLEAN_DETAIL = '''def _clean_detail(text: str, max_len: int = 250) -> str:
    """
    デュアル抽出方式:
    Phase1: メール/電話/担当者名を全文から直接抽出（送信者行は除外）
    Phase2: 業務内容マーカー以降のテキストを抽出
    表示: [連絡先] | [業務内容]  or  どちらか一方
    挨拶スキップには依存しない設計
    """
    if not text:
        return ""

    SKIP_PFXS = (
        "\\u9001\\u4fe1\\u8005:",   # 送信者:
        "\\u4ef6\\u540d:",           # 件名:
        "Subject:", "From:",
        "[LINE auto-register",
    )
    email_re = re.compile(r\'[a-zA-Z0-9._%+\\-]+@[a-zA-Z0-9.\\-]+\\.[a-zA-Z]{2,}\')
    phone_re = re.compile(r\'0[0-9]{1,4}[\\-\\s]?[0-9]{3,4}[\\-\\s]?[0-9]{4}\')
    # 担当: XX  形式（担当者/担当営業 は含まない短い行）
    contact_label_re = re.compile(r\'^\\u62c5\\u5f53[^\\u8005\\u304c]{0,3}[\\uff1a:]\\s*\\S\')

    # Phase1: 連絡先抽出
    contacts: list[str] = []
    for _line in text.split("\\n"):
        _s = _line.strip()
        if not _s:
            continue
        if any(_s.startswith(_p) for _p in SKIP_PFXS):
            continue
        if contact_label_re.match(_s) and len(_s) < 25:
            if _s not in contacts:
                contacts.append(_s)
        _em = email_re.search(_s)
        if _em and _em.group(0) not in contacts:
            contacts.append(_em.group(0))
        _ph = phone_re.search(_s)
        if _ph and len(_s) <= 20 and _ph.group(0) not in contacts:
            contacts.append(_ph.group(0))
        if len(contacts) >= 3:
            break

    # Phase2: 業務内容抽出（優先順: 業務内容 > 概要/案件 > スキル）
    MARKERS = [
        "\\u300a\\u696d\\u52d9\\u5185\\u5bb9\\u300b",  # 《業務内容》
        "\\u3010\\u696d\\u52d9\\u5185\\u5bb9\\u3011",  # 【業務内容】
        "\\u3010\\u4f5c\\u696d\\u5185\\u5bb9\\u3011",  # 【作業内容】
        "\\u3010\\u696d\\u52d9\\u6982\\u8981\\u3011",  # 【業務概要】
        "\\u696d\\u52d9\\u5185\\u5bb9\\uff1a",         # 業務内容：
        "\\u696d\\u52d9\\u5185\\u5bb9:",               # 業務内容:
        "\\u25c6\\s*\\u696d\\u52d9\\u5185\\u5bb9",     # ◆ 業務内容
        "\\u25a0\\u696d\\u52d9\\u5185\\u5bb9",         # ■業務内容
        "\\u25a0\\u4f5c\\u696d\\u5185\\u5bb9",         # ■作業内容
        "\\u3010\\u6848\\u4ef6\\u3011",                # 【案件】
        "\\u3010\\u6982\\u8981\\u3011",                # 【概要】
        "\\u25c6\\s*\\u6848\\u4ef6\\u540d",            # ◆ 案件名
        "\\u25c6\\u6848\\u4ef6\\u540d",                # ◆案件名
        "\\u25a0\\u6848\\u4ef6\\u540d",                # ■案件名
        "\\u25c6\\s*\\u30b9\\u30ad\\u30eb",            # ◆ スキル
    ]
    content = ""
    for _m in MARKERS:
        _marker = bytes([int(_m[i:i+4], 16) for i in range(0, len(_m), 4)]).decode() if False else _m
        _idx = text.find(_m)
        if _idx >= 0:
            content = re.sub(r"\\n+", " ", text[_idx:]).strip()
            break

    # 組み合わせ
    contact_str = " / ".join(contacts[:3])
    if contact_str and content:
        _avail = max_len - len(contact_str) - 3
        result = (contact_str + " | " + content[:_avail]) if _avail >= 40 else contact_str
    elif contact_str:
        result = contact_str
    elif content:
        result = content
    else:
        result = re.sub(r"\\n+", " ", text).strip()

    result = re.sub(r"\\s+", " ", result).strip()
    return (result[:max_len] + "...") if len(result) > max_len else result

'''

# ちょっと待って、上のコードのMARKERS内でUnicodeエスケープを直接findしてしまうと
# テキスト内の日本語とマッチしない。Unicodeエスケープ→実文字列に変換してから find する。
# → コードを正しく書き直す

NEW_CLEAN_DETAIL = '''def _clean_detail(text: str, max_len: int = 250) -> str:
    """
    デュアル抽出方式:
    Phase1: メール/電話/担当者名を全文から直接抽出（送信者行は除外）
    Phase2: 業務内容マーカー以降のテキストを抽出
    表示: [連絡先] | [業務内容]  or  どちらか一方
    """
    if not text:
        return ""

    # 送信者/件名行は除外
    _SKIP = (
        "\\u9001\\u4fe1\\u8005:",  # 送信者:
        "\\u4ef6\\u540d:",          # 件名:
        "Subject:", "From:", "[LINE auto-register",
    )
    _EMAIL_RE = re.compile(r\'[a-zA-Z0-9._%+\\-]+@[a-zA-Z0-9.\\-]+\\.[a-zA-Z]{2,}\')
    _PHONE_RE = re.compile(r\'0[0-9]{1,4}[\\-\\s]?[0-9]{3,4}[\\-\\s]?[0-9]{4}\')
    # 担当：阿部 のような行（担当者/担当が は除外、25文字未満）
    _CTCT_RE  = re.compile(r\'^\\u62c5\\u5f53[^\\u8005\\u304c]{0,3}[\\uff1a:]\\s*\\S\')

    # Phase1: 連絡先抽出
    contacts: list[str] = []
    for _ln in text.split("\\n"):
        _s = _ln.strip()
        if not _s:
            continue
        if any(_s.startswith(_p) for _p in _SKIP):
            continue
        if _CTCT_RE.match(_s) and len(_s) < 25:
            if _s not in contacts:
                contacts.append(_s)
        _em = _EMAIL_RE.search(_s)
        if _em:
            _e = _em.group(0)
            if _e not in contacts:
                contacts.append(_e)
        _ph = _PHONE_RE.search(_s)
        if _ph and len(_s) <= 20:
            _p2 = _ph.group(0)
            if _p2 not in contacts:
                contacts.append(_p2)
        if len(contacts) >= 3:
            break

    # Phase2: 業務内容マーカー以降抽出
    # 優先順: 業務内容 > 案件/概要 > スキル
    _MARKERS = [
        "\\u3010\\u696d\\u52d9\\u5185\\u5bb9\\u3011",       # 【業務内容】
        "\\u3010\\u4f5c\\u696d\\u5185\\u5bb9\\u3011",       # 【作業内容】
        "\\u3010\\u696d\\u52d9\\u6982\\u8981\\u3011",       # 【業務概要】
        "\\u696d\\u52d9\\u5185\\u5bb9\\uff1a",              # 業務内容：
        "\\u696d\\u52d9\\u5185\\u5bb9:",                    # 業務内容:
        "\\u300a\\u696d\\u52d9\\u5185\\u5bb9\\u300b",       # 《業務内容》
        "\\u25a0\\u696d\\u52d9\\u5185\\u5bb9",              # ■業務内容
        "\\u25a0\\u4f5c\\u696d\\u5185\\u5bb9",              # ■作業内容
        "\\u3010\\u6848\\u4ef6\\u3011",                     # 【案件】
        "\\u3010\\u6982\\u8981\\u3011",                     # 【概要】
        "\\u25c6 \\u6848\\u4ef6\\u540d\\uff1a",             # ◆ 案件名：
        "\\u25c6\\u6848\\u4ef6\\u540d\\uff1a",              # ◆案件名：
        "\\u25a0\\u6848\\u4ef6\\u540d\\uff1a",              # ■案件名：
        "\\u25c6 \\u30b9\\u30ad\\u30eb",                   # ◆ スキル
    ]
    content = ""
    for _raw_marker in _MARKERS:
        # Unicodeエスケープを実文字列に変換
        _marker = _raw_marker.encode().decode(\'unicode_escape\')
        _idx = text.find(_marker)
        if _idx >= 0:
            content = re.sub(r"\\n+", " ", text[_idx:]).strip()
            break

    # 組み合わせ
    contact_str = " / ".join(contacts)
    if contact_str and content:
        _avail = max_len - len(contact_str) - 3
        result = (contact_str + " | " + content[:_avail]) if _avail >= 40 else contact_str
    elif contact_str:
        result = contact_str
    elif content:
        result = content
    else:
        result = re.sub(r"\\n+", " ", text).strip()

    result = re.sub(r"\\s+", " ", result).strip()
    return (result[:max_len] + "...") if len(result) > max_len else result

'''

# ローカルでテスト
exec_ns = {"re": __import__("re")}
exec(NEW_CLEAN_DETAIL, exec_ns)
clean_fn = exec_ns["_clean_detail"]

test_cases = [
    (
        "音声認識",
        """【メールから自動登録】\n送信者: 阿部　茉椰 <maya.abe@liberteer.tech>\n件名: 案件情報\n\n株式会社TERRA\nご担当者様\n大変お世話になっております。\n株式会社リバティア営業部でございます。\nよろしくお願いいたします。\n担当：阿部\n携帯：080-7028-0754\nメール：maya.abe@liberteer.tech\n【案件】音声認識システム開発支援\n【概要】\nコールセンターの通話を文字に起こし""",
    ),
    (
        "Java×AI",
        """【メールから自動登録】\n送信者: WhiteBox <cx@is-tech.co.jp>\n件名: 案件\n\nお世話になっております。\n◆ 案件名： Java×AI_ブロックチェーン企業開発支援\n◆ スキル：\n・Java（Springboot）でのWEBサービス開発経験5年以上""",
    ),
    (
        "生命保険BTM",
        """【メールから自動登録】\n送信者: BTM<eigyo@b-tm.co.jp>\n件名: BTM案件\n\nお取引会社 ご担当者 様\nBTM DX推進事業本部でございます。\n\n■担当営業\n　廣奥 祐輝\n　y-hiroku@b-tm.co.jp\n　080-3436-9252\n\n■案件名： 生命保険向け販売支援・契約管理システム""",
    ),
    ("Claude Code", "業務内容：\n・生成AIを用いたソースコード解析\n・Claude Code等を活用したリライト変換"),
]

print("=== テスト結果 ===")
all_ok = True
for name, raw in test_cases:
    r = clean_fn(raw)
    bad = any(r.startswith(b) for b in ["よろしく", "でございます", "お世話", "BTM DX", "当社案件", "見合う"])
    if bad:
        all_ok = False
    print(f"{'✅' if not bad else '❌'} [{name}]")
    print(f"   {r[:120]}")
    print()

print(f"{'✅ OK' if all_ok else '❌ 要修正'}")
