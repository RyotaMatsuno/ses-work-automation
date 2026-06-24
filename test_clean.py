import io
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


# _clean_detail の改善版をテスト
def clean_detail_v2(text: str, max_len: int = 250) -> str:
    if not text:
        return ""

    # ── STEP1: 自動登録ヘッダー行を除去 ──────────────────────────
    skip_in_line = (
        "メールから自動登録",
        "[LINE auto-register",
        "送信者:",
        "件名:",
        "Subject:",
        "From:",
    )
    greet_starts = (
        "株式会社",
        "合同会社",
        "有限会社",  # 会社名で始まる行
        "ご担当者",
        "担当者様",
        "担当者 様",
        "お世話になっております",
        "お世話になります",
        "いつもお世話",
        "大変お世話",
        "BCCにて",
        "BCC\u306b\u3066",
        "該当人材",
        "見合う方",
        "見合う要員",
        "エントリーいただける",
        "ご返信の際",
        "ご紹介いただければ",
        "ご紹介をお願い",
        "下記案件",
        "よろしくお願いいたします",
        "---",
        "===",
        "＿＿＿",
        "──",
    )

    lines = text.split("\n")
    # 先頭から、有用な内容行が始まるまでスキップ
    content_lines = []
    found_content = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        is_skip = any(m in stripped for m in skip_in_line)
        is_greet = any(stripped.startswith(g) or stripped == g for g in greet_starts)
        if not found_content and (is_skip or is_greet):
            continue  # まだコンテンツが始まっていない行はスキップ
        found_content = True
        content_lines.append(stripped)

    text = " ".join(content_lines)

    # ── STEP2: 案件内容マーカーがあればその後ろから ──────────────
    content_markers = (
        "◆ 案件名",
        "◆案件名",
        "■案件名",
        "■業務内容",
        "■作業内容",
        "■業務概要",
        "【案件名】",
        "【業務内容】",
        "【作業内容】",
        "【業務概要】",
        "【業務詳細】",
        "《業務内容》",
        "＜業務内容＞",
        "業務内容：",
        "作業内容：",
        "業務概要：",
        "・業務内容",
        "・作業内容",
    )
    for m in content_markers:
        idx = text.find(m)
        if idx >= 0:
            text = text[idx:].strip()
            break

    # ── STEP3: 整形・truncate ───────────────────────────────────
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_len:
        return text[:max_len] + "..."
    return text


# テスト
test_cases = [
    # ①音声認識（挨拶文あり）
    (
        "株式会社TERRA ご担当者様\n大変お世話になっております。\n株式会社リバティア営業部でございます。\n下記案件にて技術者を探しております。\n--------------------------------\n■案件名：音声認識システム開発支援\n■業務内容：音声認識エンジンを用いたシステムの開発・改善",
        "■業務内容から開始",
    ),
    # ②Java×AI（◆マーカーあり）
    (
        "株式会社TERRA 松野 亮太様\nお世話になっております。WhiteBoxのCX推進部です。\n----------------------------------------\n◆ 案件名： Java×AI_デジタル通貨・ブロックチェーン\n◆ スキル： ・Java ・Spring Boot",
        "◆案件名から開始",
    ),
    # ③生命保険（■担当営業あり）
    (
        "お取引会社 ご担当者 様\nいつもお世話になっております。BTM DX推進事業本部でございます。\n■担当営業 廣奥 祐輝 y-hiroku@b-tm.co.jp\n===\n案件概要\nJavaを用いた生命保険販売支援システムの新規構築",
        "案件概要から開始",
    ),
    # ④Claude Code（直接内容）
    (
        "・生成AIを用いたソースコード解析\n・Claude Code等を活用したリライト変換プロセスの設計\n▼求める人物像\n・Claude Code等の生成AIを活用した開発経験",
        "そのまま",
    ),
]

for raw, desc in test_cases:
    result = clean_detail_v2(raw)
    print(f"[{desc}]")
    print(f"  → {result[:100]}")
    print()
