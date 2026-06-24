import json
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_subjects_sample.json", encoding="utf-8") as f:
    data = json.load(f)

SKIP_PATTERNS = [
    r"関西|大阪|京都|神戸|名古屋|愛知|福岡|九州|札幌|北海道|仙台|広島|静岡|沖縄|宮城|北陸|高崎|松任",
    r"セミナー|ウェビナー|説明会|ご案内|御礼|メルマガ|配信停止|プレスリリース|採用.*正社員|転職",
    r"サービス.*ご紹介|導入事例|資料請求|無料.*トライアル|キャンペーン|お知らせ",
    r"ロースキル|未経験可|アポ取り|架電|コールセンター|ポップアップ|販売|商品案内",
    r"ディレクター(?!.*開発)|Webディレク|制作ディレク",  # Web制作ディレクターはSESと違う
    r"マーケティング|コンサル(?!.*IT|.*PM|.*SAP|.*ERP)",  # IT系以外のコンサル
]

PROJECT_PATTERNS = [
    r"【案件】|【案件情報】|【PJ】|【プロジェクト】|【求人】",
    r"案件.*募集|募集.*案件|案件.*紹介|紹介.*案件",
    r"【.*(?:開発|設計|構築|運用|保守|移行|刷新|導入).*】",
    r"元請け|直案件|エンド直|元請直",
    r"CONVICTION案件|NBW案件|BTM案件",
    r"【[0-9～〜~\-–]+月.*】.*(?:Java|Python|PHP|C#|Go|AWS|インフラ|PM|PMO)",
    r"【.*万.*】.*(?:Java|Python|PHP|C#|AWS|インフラ)",
]

ENGINEER_PATTERNS = [
    r"【要員】|【人材】|【自社.*】|【BP.*】|【SES.*】|【直人材】|【直要員】|【直個人】",
    r"【弊社|【当社|弊社.*プロパー|弊社.*社員|弊社.*フリー|弊社.*個人",
    r"要員.*紹介|紹介.*要員|人材.*ご紹介|ご紹介.*人材|人材情報",
    r"即日.*参画|参画.*即日|稼働.*可能|空き.*あり|即日要員|注力要員",
    r"エンジニア.*紹介|紹介.*エンジニア",
    r"【Astro人材】|【プラウド要員】|【KAD.*】|【ビズリンク",
    r"[0-9]+万.*エンジニア|エンジニア.*[0-9]+万|～[0-9]+万|〜[0-9]+万|@[0-9]+万",
    r"【即日要員】|【6月.*要員】|【7月.*要員】|【[0-9]月.*要員】",
    r"(?:Java|Python|PHP|C#|Go|AWS|インフラ|PM|PMO).*(?:要員|人材|エンジニア)",
    r"(?:要員|人材|エンジニア).*(?:Java|Python|PHP|C#|Go|AWS|インフラ)",
    r"単価下げ|条件緩和|単価調整",
    r"【人材情報】|注力.*要員|要員.*注力",
]


def classify_by_rule(subj, frm):
    for pat in SKIP_PATTERNS:
        if re.search(pat, subj + " " + frm):
            return "skip"
    for pat in PROJECT_PATTERNS:
        if re.search(pat, subj):
            return "project"
    for pat in ENGINEER_PATTERNS:
        if re.search(pat, subj + " " + frm[:40]):
            return "engineer"
    return "unknown"


results = {"project": 0, "engineer": 0, "skip": 0, "unknown": 0}
unknown_samples = []

for item in data:
    subj = item.get("subject", "")
    frm = item.get("from", "")
    label = classify_by_rule(subj, frm)
    results[label] += 1
    if label == "unknown" and len(unknown_samples) < 30:
        unknown_samples.append({"subject": subj[:80], "from": frm[:50]})

total = len(data)
print("=== 強化版ルール 4,000件分類結果 ===")
for k, v in results.items():
    pct = v / total * 100
    bar = "█" * int(pct / 2)
    print(f"  {k:10s}: {v:4d}件 ({pct:5.1f}%) {bar}")

ai_needed = results["unknown"]
ai_pct = ai_needed / total * 100
print(f"\nAIが必要な件数: {ai_needed}件 ({ai_pct:.1f}%)")
print(f"ルールで処理できる件数: {total - ai_needed}件 ({100 - ai_pct:.1f}%)")

print("\n=== 残unknownサンプル ===")
for s in unknown_samples[:15]:
    print(f"  {s['subject']}")
