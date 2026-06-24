import io
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ── 正しい _clean_detail（Unicodeエスケープを二重デコードしない）──────────
NEW_CLEAN_DETAIL = r'''def _clean_detail(text: str, max_len: int = 250) -> str:
    """
    デュアル抽出方式（挨拶スキップなし）:
    Phase1: メール/電話/担当者名を全文から直接抽出
    Phase2: 業務内容マーカー以降のテキストを抽出
    """
    if not text:
        return ""
    _SKIP = ("\u9001\u4fe1\u8005:", "\u4ef6\u540d:", "Subject:", "From:", "[LINE auto-register")
    _EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
    _PHONE_RE = re.compile(r'0[0-9]{1,4}[\-\s]?[0-9]{3,4}[\-\s]?[0-9]{4}')
    _CTCT_RE  = re.compile(r'^\u62c5\u5f53[^\u8005\u304c]{0,3}[\uff1a:]\s*\S')
    contacts: list[str] = []
    for _ln in text.split("\n"):
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
        if len(contacts) >= 3:
            break
    _MARKERS = [
        "\u3010\u696d\u52d9\u5185\u5bb9\u3011",
        "\u3010\u4f5c\u696d\u5185\u5bb9\u3011",
        "\u3010\u696d\u52d9\u6982\u8981\u3011",
        "\u696d\u52d9\u5185\u5bb9\uff1a",
        "\u696d\u52d9\u5185\u5bb9:",
        "\u300a\u696d\u52d9\u5185\u5bb9\u300b",
        "\u25a0\u696d\u52d9\u5185\u5bb9",
        "\u25a0\u4f5c\u696d\u5185\u5bb9",
        "\u3010\u6848\u4ef6\u3011",
        "\u3010\u6982\u8981\u3011",
        "\u25c6 \u6848\u4ef6\u540d\uff1a",
        "\u25c6\u6848\u4ef6\u540d\uff1a",
        "\u25a0\u6848\u4ef6\u540d\uff1a",
        "\u25c6 \u6848\u4ef6\u540d",
        "\u25c6 \u30b9\u30ad\u30eb",
    ]
    content = ""
    for _mk in _MARKERS:
        _idx = text.find(_mk)
        if _idx >= 0:
            content = re.sub(r"\n+", " ", text[_idx:]).strip()
            break
    contact_str = " / ".join(contacts)
    if contact_str and content:
        _av = max_len - len(contact_str) - 3
        result = (contact_str + " | " + content[:_av]) if _av >= 40 else contact_str
    elif contact_str:
        result = contact_str
    elif content:
        result = content
    else:
        result = re.sub(r"\n+", " ", text).strip()
    result = re.sub(r"\s+", " ", result).strip()
    return (result[:max_len] + "...") if len(result) > max_len else result
'''

# 検証
exec_ns = {"re": re}
exec(NEW_CLEAN_DETAIL, exec_ns)
clean_fn = exec_ns["_clean_detail"]

# マーカーが正しくデコードされているか確認
print("=== マーカー確認 ===")
test_markers = ["【業務内容】", "業務内容：", "【案件】", "【概要】", "◆ 案件名：", "◆ スキル"]
for m in test_markers:
    ok = m in NEW_CLEAN_DETAIL.replace("\\n", "\n")
    print(f"  {'✅' if ok else '⚠️'} [{m}] in source")

print()

# 5ケーステスト
test_cases = [
    (
        "① 音声認識（担当連絡先→案件概要）",
        "【メールから自動登録】\n送信者: 阿部　茉椰 <maya.abe@liberteer.tech>\n件名: 案件\n\nよろしくお願いいたします。\n担当：阿部\n携帯：080-7028-0754\nメール：maya.abe@liberteer.tech\n【案件】音声認識システム開発支援\n【概要】\nコールセンターの通話を文字に起こし",
        ["担当：阿部", "maya.abe@liberteer.tech", "【案件】"],
    ),
    (
        "② Java×AI（◆案件名から）",
        "【メールから自動登録】\n送信者: WhiteBox <cx@is-tech.co.jp>\n件名: 案件\n\nお世話になっております。\n\n◆ 案件名： Java×AI_ブロックチェーン企業開発支援\n◆ スキル：\n・Java（Springboot）でのWEBサービス開発経験5年以上",
        ["◆ 案件名："],
    ),
    (
        "③ 生命保険（廣奥連絡先→■案件名）",
        "【メールから自動登録】\n送信者: BTM<eigyo@b-tm.co.jp>\n件名: BTM案件\n\nBTM DX推進事業本部でございます。\n■担当営業\n　廣奥 祐輝\n　y-hiroku@b-tm.co.jp\n　080-3436-9252\n■案件名： 生命保険向け販売支援",
        ["y-hiroku@b-tm.co.jp", "■案件名："],
    ),
    (
        "④ Claude Code（業務内容：直接）",
        "業務内容：\n・生成AIを用いたソースコード解析\n・Claude Code等を活用したリライト変換",
        ["業務内容："],
    ),
    (
        "⑤ フロントエンド（◆スキル）",
        "【メールから自動登録】\n送信者: WhiteBox <cx@is-tech.co.jp>\n件名: 案件\n\nお世話になっております。\n\n◆ 案件名： 大手インターネット事業会社でのフロントエンド開発\n◆ スキル：\n・C#でのWEB開発経験3〜5年以上",
        ["◆ 案件名："],
    ),
]

all_ok = True
for name, raw, expected_keywords in test_cases:
    result = clean_fn(raw)
    missing = [k for k in expected_keywords if k not in result]
    ok = len(missing) == 0
    if not ok:
        all_ok = False
    print(f"{'✅' if ok else '❌'} [{name}]")
    print(f"   → {result[:120]}")
    if missing:
        print(f"   ❌ 欠落キーワード: {missing}")
    print()

print(f"{'✅ 全テストOK' if all_ok else '❌ 要修正あり'}")

# BUG-A確認: remote空の場合の表示確認
print()
print("=== BUG-A 修正確認 ===")
loc, remote = "池袋", ""
old = f"  {loc}({remote})"
new = f"  {loc}" + (f"({remote})" if remote else "")
print(f"  修正前: [{old}]")
print(f"  修正後: [{new}]")
