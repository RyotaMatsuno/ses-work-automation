import io
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def clean_detail_v3(text: str, max_len: int = 250) -> str:
    """案件詳細から業務内容を抽出（改良版）"""
    if not text:
        return ""

    # ── フェーズ1: コンテンツマーカーがあればそこから開始 ──────────
    # メールでよく使われる案件説明の開始マーカー
    markers = [
        r"◆\s*案件名",
        r"◆\s*業務内容",
        r"◆\s*作業内容",
        r"■\s*業務内容",
        r"■\s*作業内容",
        r"■\s*案件概要",
        r"■\s*業務概要",
        r"【業務内容】",
        r"【作業内容】",
        r"【業務概要】",
        r"【案件概要】",
        r"《業務内容》",
        r"＜業務内容＞",
        r"〇\s*業務内容",
        r"・業務内容",
        r"・作業内容",
        r"業務内容：",
        r"業務内容:",
        r"作業内容：",
        r"作業内容:",
        r"▼業務内容",
        r"▼作業内容",
    ]
    for pattern in markers:
        m = re.search(pattern, text)
        if m:
            snippet = text[m.start() :]
            # 改行を整理して250文字
            snippet = re.sub(r"\n+", " ", snippet).strip()
            return (snippet[:max_len] + "...") if len(snippet) > max_len else snippet

    # ── フェーズ2: マーカーなし → 挨拶ブロックをスキップして本文を取得 ──
    # 行単位で見て、純粋に「有益でない行」をスキップ
    greet_patterns = [
        r"^株式会社",
        r"^合同会社",
        r"^有限会社",
        r"^一般社団法人",
        r"ご担当者",
        r"担当者様",
        r"お世話になっております",
        r"お世話になります",
        r"いつも.*お世話",
        r"大変.*お世話",
        r"^BCC",
        r"^CC",
        r"^---",
        r"^===",
        r"^＿＿",
        r"^──",
        r"該当人材がいらっしゃ",
        r"見合う方がいらっしゃ",
        r"ご紹介.*お願",
        r"ご紹介いただけ",
        r"エントリーいただける",
        r"^\s*$",  # 空行
    ]
    lines = text.split("\n")
    content_lines = []
    skipping = True
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if skipping:
            # この行がスキップ対象かチェック
            is_junk = any(re.search(p, stripped) for p in greet_patterns)
            if is_junk:
                continue
            # スキップ対象でなければここから本文
            skipping = False
        content_lines.append(stripped)

    result = " ".join(content_lines).strip()
    result = re.sub(r"\s+", " ", result)
    return (result[:max_len] + "...") if len(result) > max_len else result


# テスト
samples = [
    (
        "■業務内容あり",
        "株式会社TERRA ご担当者様\nお世話になっております。\n■業務内容\n音声認識エンジンを用いた開発。C#・Javaを使用。",
    ),
    (
        "◆マーカーあり",
        "お世話になっております。WhiteBoxです。\n◆ 業務内容：Java×AIブロックチェーン開発支援。Javaメイン。",
    ),
    (
        "マーカーなし・お取引会社",
        "お取引会社 ご担当者 様\nいつもお世話になっております。BTM DX推進事業本部でございます。\n■担当営業 廣奥 y-hiroku@b-tm.co.jp\nJavaを用いた生命保険販売支援システムの新規構築プロジェクト。",
    ),
    ("マーカーなし・直接内容", "・生成AIを用いたソースコード解析\n・Claude Code等を活用したリライト変換プロセスの設計"),
]

all_ok = True
for name, raw in samples:
    r = clean_detail_v3(raw)
    # 挨拶で始まっていないかチェック
    bad_starts = ["株式会社", "お取引会社", "いつもお世話", "お世話になっております"]
    ok = not any(r.startswith(b) for b in bad_starts)
    if not ok:
        all_ok = False
    print(f"{'✅' if ok else '❌'} [{name}]")
    print(f"  {r[:120]}")
    print()

print(f"{'✅ 全テストOK' if all_ok else '❌ 要修正'}")
