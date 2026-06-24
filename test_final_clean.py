import io
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


# ── 新しい _clean_detail を検証する ──────────────────────────────────
def clean_detail_final(text: str, max_len: int = 250) -> str:
    """
    デュアル抽出方式:
    1. 連絡先（メール/電話/担当者名）を全文から直接抽出
    2. 業務内容マーカー以降のテキストを抽出
    → [連絡先] | [業務内容] の形式で表示
    挨拶スキップには依存しない（false-negativeリスクを排除）
    """
    if not text:
        return ""

    SENDER_PREFIXES = ("送信者:", "件名:", "Subject:", "From:", "[LINE auto-register")
    email_re = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
    phone_re = re.compile(r"0[0-9]{1,4}[\-\s]?[0-9]{3,4}[\-\s]?[0-9]{4}")
    # 担当者名行: "担当：阿部" "担当者:田中" 等（短い行限定）
    contact_label_re = re.compile(r"^担当[^者が]{0,3}[：:]\s*\S")

    # ── Phase 1: 連絡先を全文から直接抽出 ──────────────────────────
    contacts = []
    for line in text.split("\n"):
        s = line.strip()
        if not s:
            continue
        if any(s.startswith(p) for p in SENDER_PREFIXES):
            continue
        # 担当者名行
        if contact_label_re.match(s) and len(s) < 25:
            if s not in contacts:
                contacts.append(s)
        # メールアドレス
        m = email_re.search(s)
        if m:
            e = m.group(0)
            if e not in contacts:
                contacts.append(e)
        # 電話番号（短い行のみ）
        m = phone_re.search(s)
        if m and len(s) <= 20:
            ph = m.group(0)
            if ph not in contacts:
                contacts.append(ph)
        if len(contacts) >= 4:
            break

    # ── Phase 2: 業務内容マーカー以降を抽出 ──────────────────────
    CONTENT_MARKERS = [
        "【案件】",
        "【概要】",
        "◆ 業務内容",
        "◆業務内容",
        "◆ 作業内容",
        "■業務内容",
        "■作業内容",
        "■案件名",
        "【業務内容】",
        "【作業内容】",
        "【業務概要】",
        "業務内容：",
        "業務内容:",
        "作業内容：",
        "◆ スキル",
        "◆スキル",
        "◆ 案件名",
        "◆案件名",
    ]
    content = ""
    for marker in CONTENT_MARKERS:
        idx = text.find(marker)
        if idx >= 0:
            content = re.sub(r"\n+", " ", text[idx:]).strip()
            break

    # ── 組み合わせ ────────────────────────────────────────────────
    contact_str = " / ".join(contacts[:3]) if contacts else ""

    if contact_str and content:
        available = max_len - len(contact_str) - 3  # " | "
        if available >= 40:
            result = f"{contact_str} | {content[:available]}"
        else:
            result = contact_str
    elif contact_str:
        result = contact_str
    elif content:
        result = content
    else:
        result = re.sub(r"\n+", " ", text).strip()

    result = re.sub(r"\s+", " ", result).strip()
    return (result[:max_len] + "...") if len(result) > max_len else result


# ─── 実際の5案件テキストで検証 ──────────────────────────────────────
raw_texts = {
    "① 音声認識": """【メールから自動登録】
送信者: 阿部　茉椰 <maya.abe@liberteer.tech>
件名: 【案件情報】★最新/7月/フルリモ/地方可/C#.net/詳細設計～（配信：阿部）

株式会社TERRA
ご担当者様

大変お世話になっております。
株式会社リバティア営業部でございます。

下記案件にて技術者を探しております。
見合う方がいらっしゃいましたら、ご紹介をお願いいたします。

よろしくお願いいたします。

※ご返信の際は以下のメールアドレスをCCに追加お願いいたします。

----------------------------------
担当：阿部
携帯：080-7028-0754
メール：maya.abe@liberteer.tech
----------------------------------

【案件】音声認識システム開発支援
【概要】
コールセンターの通話を文字に起こし、オペレーター業務の効率化を図るシステムの開発支援""",
    "② Java×AI": """【メールから自動登録】
送信者: WhiteBox CX推進部<cx-haishin-manage@is-tech.co.jp>
件名: 【Java × AI 】【リモート併用｜〜130万｜6月or7月】＿WhiteBox

株式会社TERRA
松野 亮太様

お世話になっております。
WhiteBoxのCX推進部です。

現在、下記案件に対応可能な要員様を探しております。
見合う方がいらっしゃいましたらご紹介いただけますと幸いです。

------------------------------------------------

◆ 案件名： Java×AI_デジタル通貨・ブロックチェーン企業開発支援
◆ スキル：
・Java（Springboot）でのWEBサービス開発経験5年以上""",
    "③ 生命保険": """【メールから自動登録】
送信者: BTM東京 ITエンジニアリング事業部<eigyo@b-tm.co.jp>
件名: 【BTM案件】【Max100万円】【浜松町】（生命保険向け販売支援・契約管理システム新規構築)

お取引会社 ご担当者 様

いつもお世話になっております。
BTM DX推進事業本部でございます。

当社案件のご紹介となります。

見合う要員がいらっしゃいましたら
是非、ご紹介を頂きたくお願い申し上げます。


■担当営業
　廣奥 祐輝
　y-hiroku@b-tm.co.jp
　080-3436-9252

■案件名： 生命保険向け販売支援・契約管理システム新規構築""",
    "④ Claude Code": """【メールから自動登録】
送信者: ICD案件情報（東京）<icd-partner@icd.co.jp>
件名: 急募！【生成AI｜開発｜】100万｜リモート併用可能｜6月｜ICD

協力会社様　各位

いつも大変お世話になっております。
ICDの篠崎でございます。

業務内容：
・生成AIを用いたソースコード解析（ソース→設計書生成）のツール開発
・Claude Code等を活用したリライト変換プロセスの設計""",
    "⑤ フロントエンド": """【メールから自動登録】
送信者: WhiteBox CX推進部<cx-haishin-manage@is-tech.co.jp>
件名: 【7月開始必須｜C#｜AIエージェント利用経験｜〜90万円】＿WhiteBox

株式会社TERRA
松野 亮太様

お世話になっております。
WhiteBoxのCX推進部です。

----------------------------------------

◆ 案件名： 大手インターネット事業会社でのフロントエンド開発
◆ スキル：
・C#でのWEBアプリケーション開発経験3〜5年以上""",
}

print("=== clean_detail_final テスト ===")
print()
all_ok = True
for name, raw in raw_texts.items():
    result = clean_detail_final(raw)
    # チェック: 挨拶文で始まっていないか
    bad_starts = [
        "よろしく",
        "でございます",
        "お世話になっております",
        "当社案件",
        "見合う",
        "ご紹介をお願い",
        "大変お世話",
    ]
    starts_bad = any(result.startswith(b) for b in bad_starts)
    if starts_bad:
        all_ok = False
    print(f"{'❌' if starts_bad else '✅'} {name}")
    print(f"   → {result[:120]}")
    print()

print(f"{'✅ 全テストOK' if all_ok else '❌ 要修正'}")
