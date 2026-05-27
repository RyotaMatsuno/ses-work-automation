
import sys, json, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

with open(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_subjects_sample.json', encoding='utf-8') as f:
    data = json.load(f)

SKIP_PATTERNS = [
    r'関西|大阪|京都|神戸|名古屋|愛知|福岡|九州|札幌|北海道|仙台|広島|静岡|沖縄|宮城|北陸|高崎|松任|茨城|栃木|群馬|新潟|長野|山梨|浜松|岡山|山口|徳島|香川|愛媛|高知|佐賀|長崎|熊本|大分|宮崎|鹿児島|埼玉県(?!.*都内|.*東京)|神奈川県(?!.*東京)',
    r'セミナー|ウェビナー|説明会|ご案内|御礼|メルマガ|配信停止|プレスリリース',
    r'サービス.*ご紹介|導入事例|資料請求|無料.*トライアル|キャンペーン',
    r'ロースキル|未経験可|アポ取り|架電業務|コールセンター|ポップアップ|販売スタッフ|商品案内',
    r'採用情報|正社員募集|求人.*正社員|転職.*支援',
    r'ハコベル',
    # 除外：外国籍・地方駅
    r'中国籍|韓国籍|ベトナム籍|外国籍',
]

ENGINEER_PATTERNS = [
    r'【直人材】|【直要員】|【直個人】|【直BP】|【SPONTO直個人】',
    r'【弊社|弊社.*プロパー|弊社.*社員|弊社.*フリー|弊社.*個人|弊社実績',
    r'【要員】|【人材】|【要員配信】|【人材情報】|注力要員|人材情報',
    r'【Astro人材】|【プラウド要員】|【KAD|【ビズリンク|【GLITTERS|【BTM|【NBW|【アイル要員|【SPONTO|【実績あり所属',
    r'[／/](?:[0-9]+歳|[0-9]+年).*(?:男性|女性)',
    r'(?:男性|女性)／.*(?:万円|万$|\d+万)',
    r'即日.*(?:要員|参画|稼働)|(?:要員|参画).*即日|稼働.*可能|空き.*あり',
    r'【即日要員】|即〜【|即日【',
    r'【[0-9]月.*要員】|[0-9]月.*要員.*紹介|要員.*[0-9]月',
    r'【(?:Java|Python|PHP|C#|Go|TypeScript|JavaScript|AWS|インフラ|PM|PMO|VB|\.NET|Delphi|COBOL|SAP|Flutter|Swift|Kotlin|React|Vue|Next\.js|Angular|Docker|Kubernetes|GCP|Azure|Oracle|SQL|Linux|Ruby|Perl|C\+\+|C言語|Unity|Power\s*BI|Tableau).*[0-9]+年】',
    r'(?:Java|Python|PHP|C#|\.NET|VB|Flutter|Swift|Kotlin|React|Vue|PMO|Unity|COBOL).*[／/][0-9]+歳',
    r'[0-9]+万.*エンジニア|エンジニア.*[0-9]+万|[～〜~][0-9]+万|[0-9]+[〜～~][0-9]+万',
    r'@[0-9]+万|／[0-9]+万|・[0-9]+万|/[0-9]+万',
    r'単価下げ|条件緩和|単価調整|単価.*相談',
    r'常駐可.*(?:弊社|当社|PM|PMO|Java|インフラ)|【実績あり',
    r'[A-Z]{2,4}[0-9]{3,4}のご紹介|のご紹介です',
    r'★大特価|大特価',
    r'【Java/C#人材】|【Java.*人材】|【.*人材】(?=.*万)',
    r'増員枠|弊社増員',
    r'【提案のお願い】',  # 案件紹介依頼
]

PROJECT_PATTERNS = [
    r'【案件】|【案件情報】|【PJ】|【プロジェクト】|【求人】',
    r'案件.*募集|募集.*案件|案件.*紹介|紹介.*案件',
    r'CONVICTION案件|NBW案件|BTM案件|【.*案件情報】|【.*注力案件】|【.*案件一覧】|ICD案件',
    r'【.*(?:開発|設計|構築|運用|保守|移行|刷新|導入|リプレース|DX).*】',
    r'元請け|直案件|エンド直|元請直|エンド顧客|現場直',
    r'【[0-9]月[〜～~/].*(?:Java|Python|PHP|C#|AWS|インフラ|PM|PMO|SQL|開発|設計|構築)】',
    r'≪急募≫|《急募》|★.*ICD案件',
    r'(?:Java|Python|PHP|C#|AWS|インフラ|PMO|SQL|COBOL).*(?:豊洲|渋谷|新宿|品川|銀座|丸の内|大手町|秋葉原|上野|池袋|赤坂|六本木|恵比寿|目黒|五反田|浜松町|田町|芝|汐留|八丁堀|茅場町|水道橋|飯田橋|市ヶ谷|四谷|新橋|虎ノ門|永田町|霞ヶ関|東京駅|新宿駅)',
    r'【7月.*開発】|【[0-9]月開始.*募集】|[0-9]月開始.*募集|募集.*[0-9]月開始',
    r'COBOL案件|汎用系.*案件|若手歓迎.*案件',
]

def classify_by_rule(subj, frm):
    for pat in SKIP_PATTERNS:
        if re.search(pat, subj + ' ' + frm):
            return 'skip'
    for pat in ENGINEER_PATTERNS:
        if re.search(pat, subj + ' ' + frm[:50]):
            return 'engineer'
    for pat in PROJECT_PATTERNS:
        if re.search(pat, subj):
            return 'project'
    return 'unknown'

results = {'project': 0, 'engineer': 0, 'skip': 0, 'unknown': 0}
unknown_samples = []

for item in data:
    subj = item.get('subject', '')
    frm = item.get('from', '')
    label = classify_by_rule(subj, frm)
    results[label] += 1
    if label == 'unknown' and len(unknown_samples) < 30:
        unknown_samples.append(subj[:90])

total = len(data)
print(f"=== 最終版v2 4,000件分類結果 ===")
for k, v in results.items():
    pct = v/total*100
    bar = '█' * int(pct/2)
    print(f"  {k:10s}: {v:4d}件 ({pct:5.1f}%) {bar}")

ai_needed = results['unknown']
ai_pct = ai_needed / total * 100
rule_pct = 100 - ai_pct
print(f"\nルール処理: {total-ai_needed}件 ({rule_pct:.1f}%) → AIコスト不要")
print(f"AI必要:    {ai_needed}件 ({ai_pct:.1f}%)")

# コスト再試算
HAIKU_IN  = 0.8 / 1e6
HAIKU_OUT = 4.0 / 1e6
USD_JPY = 155
daily_total = 2700

# unknownのみHaikuで分類（件名+冒頭200文字 = 約300tokens）
ai_per_day = daily_total * (ai_pct / 100)
haiku_classify_cost = ai_per_day * (300 * HAIKU_IN + 50 * HAIKU_OUT)

# 案件・人材はHaikuで抽出・登録（本文200文字制限）
proj_per_day = daily_total * (results['project'] / total)
eng_per_day = daily_total * (results['engineer'] / total)
# 案件: 抽出(Haiku)+マッチング(Haiku)+提案文(Haiku)
proj_cost = proj_per_day * ((600*HAIKU_IN + 100*HAIKU_OUT) + (1500*HAIKU_IN + 400*HAIKU_OUT) + (1500*HAIKU_IN + 600*HAIKU_OUT))
# 人材: 抽出(Haiku)+照合(Haiku)
eng_cost = eng_per_day * ((600*HAIKU_IN + 100*HAIKU_OUT) + (800*HAIKU_IN + 200*HAIKU_OUT))

daily_usd = haiku_classify_cost + proj_cost + eng_cost
monthly_usd = daily_usd * 22

print(f"\n=== コスト再試算（1日{daily_total}件） ===")
print(f"Haiku分類（unknown {ai_pct:.0f}%のみ）: ${haiku_classify_cost:.3f}/日")
print(f"案件処理（Haiku全面）: ${proj_cost:.3f}/日")
print(f"人材処理（Haiku全面）: ${eng_cost:.3f}/日")
print(f"合計: ${daily_usd:.3f}/日 / 約{daily_usd*USD_JPY:.0f}円/日")
print(f"月次（22日）: ${monthly_usd:.2f} / 約{monthly_usd*USD_JPY:,.0f}円")
print(f"\n現状比: ${1220:.0f}/月 → ${monthly_usd:.1f}/月（{(1-monthly_usd/1220)*100:.0f}%削減）")

print(f"\n残unknown件名サンプル（上位20件）:")
for s in unknown_samples[:20]:
    print(f"  {s}")
