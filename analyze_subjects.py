
import sys, json, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

with open(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_subjects_sample.json', encoding='utf-8') as f:
    data = json.load(f)

# ルールベース分類の定義
SKIP_PATTERNS = [
    # 地方
    r'関西|大阪|京都|神戸|名古屋|愛知|福岡|九州|札幌|北海道|仙台|広島|静岡|埼玉|千葉(?!市)|横浜|神奈川|沖縄',
    # SES無関係
    r'セミナー|ウェビナー|ウェブイナー|説明会|ご案内|御礼|メルマガ|配信停止|プレスリリース|採用|求人.*正社員|転職',
    # 営業・マーケ系
    r'サービス.*ご紹介|導入事例|資料請求|無料.*トライアル|キャンペーン|お知らせ',
]

PROJECT_PATTERNS = [
    r'【案件】|【案件情報】|【求人】|【PJ】|【プロジェクト】',
    r'案件.*募集|募集.*案件|案件.*紹介|紹介.*案件',
    r'【.*開発.*】|【.*設計.*】|【.*構築.*】|【.*運用.*】|【.*保守.*】',
    r'元請け|直案件|エンド直',
]

ENGINEER_PATTERNS = [
    r'【要員】|【人材】|【弊社.*】|【自社.*】|【BP.*】|【SES.*】',
    r'要員.*紹介|紹介.*要員|人材.*ご紹介|ご紹介.*人材',
    r'即日.*参画|参画.*即日|稼働.*可能|空き.*あり',
    r'エンジニア.*紹介|紹介.*エンジニア',
    r'弊社.*プロパー|弊社.*社員|弊社.*フリー|弊社.*個人事業',
    r'単価.*万|[0-9]+万.*エンジニア|エンジニア.*[0-9]+万',
]

def classify_by_rule(subj, frm):
    # スキップ判定
    for pat in SKIP_PATTERNS:
        if re.search(pat, subj + frm):
            return 'skip'
    # 案件判定
    for pat in PROJECT_PATTERNS:
        if re.search(pat, subj):
            return 'project'
    # 人材判定
    for pat in ENGINEER_PATTERNS:
        if re.search(pat, subj + frm[:30]):
            return 'engineer'
    return 'unknown'

results = {'project': 0, 'engineer': 0, 'skip': 0, 'unknown': 0}
unknown_samples = []

for item in data:
    subj = item.get('subject', '')
    frm = item.get('from', '')
    label = classify_by_rule(subj, frm)
    results[label] += 1
    if label == 'unknown' and len(unknown_samples) < 50:
        unknown_samples.append({'subject': subj[:80], 'from': frm[:50]})

total = len(data)
print(f"=== 4,000件ルールベース分類結果 ===")
for k, v in results.items():
    pct = v/total*100
    print(f"  {k}: {v}件 ({pct:.1f}%)")

print(f"\n=== unknownサンプル（AIが必要な件）===")
for s in unknown_samples[:20]:
    print(f"  SUBJ: {s['subject']}")
    print(f"  FROM: {s['from']}")
    print()

# 結果をJSONに保存
with open(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\classification_result.json', 'w', encoding='utf-8') as f:
    json.dump({'results': results, 'unknown_samples': unknown_samples}, f, ensure_ascii=False, indent=2)
