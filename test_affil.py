import io
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# _affil_contact のロジックをテスト（全パターン）
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
SENDER_RE = re.compile(r"(?:送信元|送信者)[:\s：]+(.{1,80}?)(?:\s*/\s*受信日|$)", re.DOTALL)


def affil_contact(affil, affil_cont, affil_mail, memo):
    """所属連絡先の表示文字列を返す（空ならNone）"""
    # 1. PROP_AFFIL に日本語が含まれている → 正規のデータ
    if affil and any("\u3000" <= c or "\u4e00" <= c <= "\u9fff" for c in affil):
        parts = [p for p in [affil, affil_cont, affil_mail] if p]
        return " / ".join(parts) if parts else None

    if not memo:
        return None

    # 2. 自社社員（手動登録）
    if "手動登録" in memo and "弊社社員" in memo:
        return "\u81ea\u793e\u793e\u54e1"  # 自社社員

    # 3. メール登録（[自動取込]）→ 送信元から抽出
    m = SENDER_RE.search(memo)
    if m:
        sender_raw = m.group(1).strip()
        email_m = EMAIL_RE.search(sender_raw)
        if email_m:
            email = email_m.group(0)
            # 名前部分（メールの前）を抽出
            before = sender_raw[: sender_raw.find(email)].strip().rstrip("<").strip()
            # 不要な記号を除去
            before = re.sub(r"^[<\s]+|[>\s]+$", "", before)
            parts = [p for p in [before, email] if p]
            return " / ".join(parts[:2])
        return sender_raw[:40] if sender_raw else None

    # 4. LINE登録（情報なし）
    return None


# テスト
test_cases = [
    # (affil, cont, mail, memo, 期待値の一部)
    (
        "",
        "",
        "",
        "[自動取込] 件名: 弊社社員7月～ / 送信元: r.takahashi@gatlab.co.jp / 受信日: ...",
        "r.takahashi@gatlab.co.jp",
    ),
    ("", "", "", "[自動取込] 件名: F.J案件 / 送信元: 藤巻 盛<mori.fujimaki@roots-tec.co.jp> / 受信日: ...", "藤巻 盛"),
    (
        "",
        "",
        "",
        "[自動取込] 件名: 会社案件 / 送信元: 株式会社ビズリンク<partner@bizlink.io> / 受信日: ...",
        "partner@bizlink.io",
    ),
    ("", "", "", "[手動登録】弊社社員。准委任。即日開始。", "自社社員"),
    ("Staffing company employee", "", "", "[LINE auto-register: matsuno]\n55-year-old male", None),  # H.S
    ("株式会社ABC", "田中一郎", "tanaka@abc.co.jp", "", "ABC"),  # 正規データ
]

print("=== _affil_contact テスト ===")
all_ok = True
for affil, cont, mail, memo, expected_contains in test_cases:
    result = affil_contact(affil, cont, mail, memo)
    ok = (expected_contains is None and result is None) or (
        expected_contains is not None and result is not None and expected_contains in result
    )
    if not ok:
        all_ok = False
    print(f"{'✅' if ok else '❌'} 結果: [{result}]  期待含む: [{expected_contains}]")

print()
print(f"{'✅ 全テストOK' if all_ok else '❌ 要修正'}")
