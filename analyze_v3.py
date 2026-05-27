
import sys, json, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

with open(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_subjects_sample.json', encoding='utf-8') as f:
    data = json.load(f)

# ===== 最終版ルール =====

SKIP_PATTERNS = [
    r'関西|大阪|京都|神戸|名古屋|愛知|福岡|九州|札幌|北海道|仙台|広島|静岡|沖縄|宮城|北陸|高崎|松任|茨城|栃木|群馬|新潟|長野|山梨|浜松|岡山|山口|徳島|香川|愛媛|高知|佐賀|長崎|熊本|大分|宮崎|鹿児島',
    r'セミナー|ウェビナー|説明会|ご案内|御礼|メルマガ|配信停止|プレスリリース',
    r'サービス.*ご紹介|導入事例|資料請求|無料.*トライアル|キャンペーン',
    r'ロースキル|未経験可|アポ取り|架電業務|コールセンター|ポップアップ|販売スタッフ|商品案内',
    r'採用情報|正社員募集|求人.*正社員|転職.*支援',
    r'ハコベル|物流.*システム(?!.*開発)',
]

# 人材判定（先に判定：件名に年齢・スキル・万円が入る特徴的パターン）
ENGINEER_PATTERNS = [
    # 【直人材】【直要員】【直個人】系
    r'【直人材】|【直要員】|【直個人】|【直BP】',
    # 【弊社】系
    r'【弊社|弊社.*プロパー|弊社.*社員|弊社.*フリー|弊社.*個人|弊社実績',
    # 【要員】【人材】明示
    r'【要員】|【人材】|【要員配信】|【人材情報】|注力要員|人材情報',
    # 会社名ブランド（Astro・プラウド・KAD・ビズリンク等）
    r'【Astro人材】|【プラウド要員】|【KAD|【ビズリンク|【GLITTERS|【BTM|【NBW',
    # 「年齢・性別・スキル列挙型」件名（例：【Java・C#・Python／14年】57歳・男性）
    r'[／/](?:[0-9]+歳|[0-9]+年).*(?:男性|女性)',
    r'(?:男性|女性)／.*(?:万円|万$|\d+万)',
    # 即日・稼働系
    r'即日.*(?:要員|参画|稼働)|(?:要員|参画).*即日|稼働.*可能|空き.*あり',
    r'【即日要員】|即〜【|即日【',
    # 月指定要員
    r'【[0-9]月.*要員】|[0-9]月.*要員.*紹介|要員.*[0-9]月',
    # スキル+年齢/単価の組み合わせ
    r'【(?:Java|Python|PHP|C#|Go|TypeScript|JavaScript|AWS|インフラ|PM|PMO|VB|\.NET|Delphi|COBOL|SAP|Flutter|Swift|Kotlin|React|Vue|Next\.js|Angular|Docker|Kubernetes|GCP|Azure|Oracle|SQL|Linux|Ruby|Perl|C\+\+|C言語).*[0-9]+年】',
    r'(?:Java|Python|PHP|C#|\.NET|VB|Flutter|Swift|Kotlin|React|Vue|PMO).*[／/][0-9]+歳',
    # 単価万円パターン
    r'[0-9]+万.*エンジニア|エンジニア.*[0-9]+万|[～〜~][0-9]+万|[0-9]+[〜～~][0-9]+万',
    r'@[0-9]+万|／[0-9]+万|・[0-9]+万',
    # その他
    r'単価下げ|条件緩和|単価調整|単価.*相談',
    r'常駐可.*(?:弊社|当社|PM|PMO|Java|インフラ)',
    r'【[A-Z].*[0-9]+のご紹介】|のご紹介です',
]

PROJECT_PATTERNS = [
    # 明示的案件タグ
    r'【案件】|【案件情報】|【PJ】|【プロジェクト】|【求人】',
    r'案件.*募集|募集.*案件|案件.*紹介|紹介.*案件',
    # 会社名ブランドの案件
    r'CONVICTION案件|NBW案件|BTM案件|【.*案件情報】|【.*注力案件】',
    # 業務内容が先頭に来るパターン
    r'【(?:Java|Python|PHP|C#|Go|TypeScript|JavaScript|AWS|インフラ|PM|PMO|SAP|Oracle|SQL|Linux|Flutter|Swift|Kotlin|React|Vue|Next\.js|Angular|Docker|Kubernetes|GCP|Azure|Ruby|C\+\+|C言語|\.NET|VB|Delphi|COBOL).*(?:開発|設計|構築|運用|保守|移行|導入|刷新)】',
    r'【.*(?:開発|設計|構築|運用|保守|移行|刷新|導入|リプレース|DX).*】',
    # 元請け・直案件
    r'元請け|直案件|エンド直|元請直|エンド顧客',
    # 月～スタートで業務内容が続くパターン
    r'【[0-9]月[〜～~/].*(?:Java|Python|PHP|C#|AWS|インフラ|PM|PMO|SQL|開発|設計|構築)】',
    r'≪急募≫|《急募》',
    # 業務内容系（スキル+勤務地）
    r'(?:Java|Python|PHP|C#|AWS|インフラ|PMO|SQL).*(?:豊洲|渋谷|新宿|品川|銀座|丸の内|大手町|秋葉原|上野|池袋|赤坂|六本木|恵比寿|目黒|五反田|浜松町|田町|芝|汐留|八丁堀|茅場町|水道橋|飯田橋|市ヶ谷|四谷|新橋|虎ノ門|永田町|霞ヶ関)',
]

def classify_by_rule(subj, frm):
    # スキップ
    for pat in SKIP_PATTERNS:
        if re.search(pat, subj + ' ' + frm):
            return 'skip'
    # 人材（先に判定：スキル+年齢/万円パターンが案件と区別しやすい）
    for pat in ENGINEER_PATTERNS:
        if re.search(pat, subj + ' ' + frm[:50]):
            return 'engineer'
    # 案件
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
    if label == 'unknown' and len(unknown_samples) < 40:
        unknown_samples.append(f"{subj[:80]}")

total = len(data)
print(f"=== 最終版ルール 4,000件分類結果 ===")
for k, v in results.items():
    pct = v/total*100
    bar = '█' * int(pct/2)
    print(f"  {k:10s}: {v:4d}件 ({pct:5.1f}%) {bar}")

ai_needed = results['unknown']
ai_pct = ai_needed / total * 100
print(f"\nAIが必要: {ai_needed}件 ({ai_pct:.1f}%)")
print(f"ルール処理: {total-ai_needed}件 ({100-ai_pct:.1f}%)")
print(f"\n残unknown件名サンプル:")
for s in unknown_samples[:20]:
    print(f"  {s}")
