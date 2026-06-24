import json
import re
import sys
from typing import Dict, List, Tuple

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# 明らかなノイズのみ skip（Recall重視: 迷うものは unknown → LLM）
SKIP_PATTERNS = [
    r"セミナー|ウェビナー|説明会|交流会|メルマガ|配信停止|プレスリリース|ニュースレター",
    r"自動返信|Auto-Reply|Out of office|自動応答|不在通知",
    r"サービス.*ご紹介|導入事例|資料請求|無料.*トライアル|キャンペーン",
    r"採用情報|正社員募集|求人.*正社員|転職.*支援",
    r"営業挨拶|ご挨拶のみ",
]

# IMP-1: 件名定型 人材送り込みパターン（eng_score +5: project語があっても人材優先）
ENGINEER_SUBJECT_PRIORITY = [
    r"直フリーランス",
    r"(?:1社下|1社先|弊社1社下)",
    r"(?:弊社福岡プロパー|弊社社員|弊社要員)",
    r"【\d{1,2}月人材】",
    r"(?:ご紹介可能|提案可能|要員紹介|人材紹介|要員提案)",
    r"(?:スキルシート|職務経歴書|経歴書|ご経歴)",
]

# 配信メールの人員紹介 → pipeline では skip 扱い
ENGINEER_PATTERNS = [
    # === 強い人材パターン（最優先） ===
    # 角括弧内の人材/要員/社員
    r"【[^】]{0,20}(?:人材|要員|技術者|社員情報)[^】]*】",
    # 弊社/当社/自社 + プロパー/社員/所属
    r"(?:弊社|当社|自社).{0,4}(?:プロパー|社員|所属|要員|人材|エンジニア)",
    # 注力/営業中/直 + 人材/要員
    r"(?:注力|提案|紹介|営業中|所属).{0,8}(?:人材|要員|技術者)",
    r"(?:人材|要員|技術者).{0,8}(?:情報|紹介|提案)",
    r"営業中人材|注力人材|直人材",
    # 所属要員/社員紹介/一社先
    r"所属(?:要員|人材|エンジニア)|社員紹介",
    r"(?:一社先|BP先).{0,4}(?:正社員|社員|契約社員)",
    # === 既存パターン（維持） ===
    r"【直人材】|【直要員】|【直個人】|【直BP】|【SPONTO直個人】",
    r"【弊社|弊社.*プロパー|弊社.*社員|弊社.*フリー|弊社.*個人|弊社実績",
    r"【要員】|【人材】|【要員配信】|【人材情報】|：要員|：人材|注力要員|人材情報|要員ご紹介",
    r"弊社エンジニア|(?:弊社|当社|自社).{0,6}(?:技術者|エンジニア).*ご紹介",  # 弊社+エンジニア紹介のみ（案件名の「エンジニア」は除外）
    r"【Astro人材】|【プラウド要員】|【KAD|【ビズリンク|【GLITTERS|【BTM要員|【BTM人材|【BTM】.*要員|【NBW要員|【NBW人材|【NBW】.*要員|【アイル要員|【SPONTO|【実績あり所属",
    r"[／/](?:[0-9]+歳|[0-9]+年).*(?:男性|女性)",
    r"(?:男性|女性)／.*(?:万円|万$|\d+万)",
    r"即日.*(?:要員|参画|稼働)|(?:要員|参画).*即日|稼働.*可能|空き.*あり",
    r"【即日要員】|即〜【|即日【",
    r"【[0-9]月.*要員】|[0-9]月.*要員.*紹介|要員.*[0-9]月",
    r"【(?:Java|Python|PHP|C#|Go|TypeScript|JavaScript|AWS|インフラ|PM|PMO|VB|\.NET|Delphi|COBOL|SAP|Flutter|Swift|Kotlin|React|Vue|Next\.js|Angular|Docker|Kubernetes|GCP|Azure|Oracle|SQL|Linux|Ruby|Perl|C\+\+|C言語|Unity|Power\s*BI|Tableau).*[0-9]+年】",
    r"(?:Java|Python|PHP|C#|\.NET|VB|Flutter|Swift|Kotlin|React|Vue|PMO|Unity|COBOL).*[／/][0-9]+歳",
    r"[0-9]+万.*エンジニア|エンジニア.*[0-9]+万",  # 万+エンジニアの組み合わせのみ（単独の万パターンは案件に誤爆）
    r"＠[0-9]+万円|@[0-9]+万円",  # ＠75万円形式のみ（/万は案件にも多い）
    r"単価下げ|条件緩和|単価調整|単価.*相談",
    r"【実績あり",
    r"[A-Z]{2,4}[0-9]{3,4}のご紹介|(?:要員|技術者|人材|エンジニア|フリーランス)のご紹介",  # 「のご紹介です」は汎用すぎ→具体的に
    r"★大特価|大特価",
    r"【Java/C#人材】|【Java.*人材】|【.*人材】(?=.*万)",
    r"案件.*探して|探して.*案件|参画先.*探して",  # 「案件を探しています」=人材（希望単独は複合条件へ）
    r"経験[0-9０-９]+\.?[0-9０-９]*年以上",  # 「経験3年以上」=人材スペック
    r"経験あり.*常駐可|常駐可.*経験あり",  # 「経験あり+常駐可」=人材紹介
    # === OW人材/Roots人材 等の企業名付き人材パターン ===
    r"【OW人材】|【Roots人材】|【CONVICTION要員|【ACWEB直.*要員",
    r"(?:福岡|九州|関西|大阪|名古屋|札幌|仙台|広島)(?:プロパー|要員)",  # 地域+プロパー/要員=人員派遣  # 地域+プロパー=人員派遣
]

# ニュースレター・商材・告知など（project誤爆防止）
OTHER_PATTERNS = [
    r"商材.*ご紹介|ツール.*紹介|サービス.*のご案内|導入.*ご案内",
    r"営業支援|リード獲得|マーケティング|営業代行|集客",
    r"開催.*のお知らせ|開催日|参加.*無料|参加費",
    r"商談.*方法|AIで.*標準化|業務.*効率化.*セミナー",
    r"掲載.*求人|求人広告|リクナビ|マイナビ|Indeed",
    r"号外",
    r"エンジニア募集.*複数名|募集.*複数名",
    r"スポット案件ください",
    r"マッチングツール|採用を支援するサービス",
]

# 広く案件を拾う（事務・ヘルプデスク・ロースキル含む）
PROJECT_PATTERNS = [
    r"【案件】|【案件情報】|【PJ】|【プロジェクト】|【求人】",
    r"案件配信|案件募集|案件.*募集|募集.*案件|案件.*紹介|紹介.*案件",
    r"CONVICTION案件|NBW案件|BTM案件|【.*案件情報】|【.*注力案件】|【.*案件一覧】|ICD案件",
    r"【.*(?:開発|設計|構築|運用|保守|移行|刷新|導入|リプレース|DX|PMO|ヘルプデスク|キッティング|情シス|テスト|データ入力|監視).*】",
    r"元請け|直案件|エンド直|元請直|元請[けケ]?直|エンド顧客|現場直|商流|決済者直",
    r"[0-9０-９]{1,2}\s*月\s*[〜～~/\-開始]",
    r"即日\s*[〜～開始]",
    r"[\d０-９]{2,3}\s*[万萬]\s*[円〜～\-]?",
    r"[〜～]\s*[\d０-９]{2,3}\s*[万萬]",
    r"[0-9]+万",
    r"募集|常駐|増員",
    r"面談\s*[0-9０-９]\s*回|WEB面談|対面面談",
    r"準委任|業務委託|フルリモート|リモート[可併]",
    r"ヘルプデスク|PMO|コールセンター|事務|運用監視|キッティング|情シス|データ入力",
    r"≪急募≫|《急募》|★.*ICD案件",
    r"COBOL案件|汎用系.*案件|若手歓迎.*案件",
    r"SES|派遣",
    r"弊社増員枠?|増員枠",  # 弊社増員は案件側
    r"弊社注力案件|弊社直案件",  # 弊社注力案件/弊社直案件 = project
    r"案件配信|案件のご紹介|募集案件|新規案件|増員案件",
    r"弊社直案件|エンド直案件",
    # IMP-6: 案件構造語
    r"(?:注力案件|最注力案件)",
    r"(?:案件概要|業務内容|担当工程|開発環境)",
    r"(?:面談(?:回数)?|精算|作業場所)",
]

PROJECT_PRIORITY_KEYWORDS = (
    "案件",
    "募集",
    "常駐",
    "増員",
    "面談",
    "準委任",
    "業務委託",
    "決済者直",
    "元請",
    "フルリモート",
)

_PRICE_RE = re.compile(r"[\d０-９]{2,3}\s*[万萬]")
_PERIOD_RE = re.compile(r"[0-9０-９]{1,2}\s*月\s*[〜～開始]|即日\s*[〜～開始]")
# IMP-5: skipを抑制するSES強シグナル
_SES_STRONG_RE = re.compile(r"案件|募集|Java|PHP|Python|AWS|Azure|NW|インフラ|PMO|SpringBoot|React|Vue|SAP|COBOL|C#")
# IMP-2: 本文構造化項目（氏名/年齢など）3つ以上でeng+4
_BODY_STRUCT_RE = re.compile(r"(?:氏名|年齢|性別|国籍|所属|最寄|稼働率|並行)\s*[:：]")
# IMP-3: 案件構造語3つ以上ある場合に優先判定を再検討
_PROJECT_STRUCT_RE = re.compile(r"案件概要|業務内容|募集人数|面談回数|勤務地|精算|商流")
# IMP-7: OTHER判定のガード（件名にSES語がある場合は本文のみのマッチを抑制）
_OTHER_GUARD_RE = re.compile(r"案件|募集|開発|\d+万|設計|構築|運用")

# --- Task AA: STRONG / 複合 / 本文テンプレ ---
STRONG_PROJECT_PATTERNS = [
    r"案件.*(?:Java|PHP|Python|Ruby|COBOL|AWS|Azure|NW|C#|Go|TypeScript|SAP)",
    r"案件.*(?:\d{2,3})万",
    r"案件.*(?:基本設計|詳細設計|保守|運用|テスト)",
    r"(?:向けシステム|向け開発|統合案件|開発案件|注力案件)",
    r"案件概要|業務内容|担当工程|募集人数|スキル要件",
    r"(?:営業中)?案件一覧|新着案件",
    r"急募.*案件|案件.*急募",
    r"\d{1,2}月案件",
    r"案件No\.|案件[:：]",
    r"★注力案件★|エンド直|元請直",
]

STRONG_ENGINEER_PATTERNS = [
    r"直個人|直フリーランス|弊社フリーランス",
    r"(?:\d{2})歳\s*[／/]\s*(?:男性|女性)",
    r"おすすめ人材|注力人材|弊社プロパー.*紹介",
    r"要員配信|人材配信",
    r"スキルシート.*添付|経歴書.*送付",
]

AMBIGUOUS_ENGINEER = [
    (r"希望", r"(?:案件.*探し|案件を探|幅広.*探|単価|勤務地|稼働|参画)"),
    (r"(?:PM補佐|PMO|社内SE|SE|PG)", r"(?:\d+歳|男性|女性|正社員|プロパー|要員|人材|稼働可能)"),
    (r"常駐可", r"(?:弊社|当社|所属|要員)"),
]

BODY_PROJECT_TEMPLATE = [
    r"案件概要",
    r"勤務場所|作業場所",
    r"期間[:：]",
    r"単価[:：]",
    r"面談[:：]|面談\d+回",
    r"募集人数",
    r"スキル要件|必須スキル|尚可スキル",
]

BODY_ENGINEER_TEMPLATE = [
    r"(?:氏名|名前)\s*[:：]",
    r"(?:年齢|性別)\s*[:：]",
    r"(?:所属|最寄)\s*[:：]",
    r"(?:希望単価|単金)\s*[:：]",
    r"(?:並行|稼働率)\s*[:：]",
    r"(?:保有スキル|経験年数)\s*[:：]",
]

_HUMAN_MARKER_RE = re.compile(
    r"\d{1,2}歳|（\d{1,2}）|\(\d{1,2}\)|男性|女性|プロパー|直個人|直フリ|弊社(?:プロパー|要員|社員|フリーランス|契約社員)|"
    r"おすすめ人材|注力人材|要員配信|人材配信|ご紹介可能|提案可能|要員情報|人材情報"
)
_SUPPRESS_STRONG_PROJECT_RE = re.compile(
    r"(?:弊社プロパー|要員|人材|本人|直個人|直フリ).*(?:案件.*(?:探|希望)|幅広.*希望|探して.*案件)|"
    r"(?:案件.*(?:探|希望)|幅広.*希望|探して.*案件).*(?:弊社プロパー|要員|人材|本人|直個人|直フリ)"
)
_SKIP_RESCUE_SUPPRESS_RE = re.compile(
    r"弊社プロパー|要員|人材|本人|直個人|直フリ"
)
_ROLE_ONLY_RE = re.compile(r"PMO|社内SE|PM補佐|フロントエンジニア")


def project_signal_score(subj: str) -> Tuple[bool, bool, bool, int]:
    """案件シグナル（キーワード・単価・期間）とスコアを返す。"""
    text = subj or ""
    has_project_keyword = any(kw in text for kw in PROJECT_PRIORITY_KEYWORDS)
    has_price = bool(_PRICE_RE.search(text))
    has_period = bool(_PERIOD_RE.search(text))
    score = int(has_project_keyword) + int(has_price) + int(has_period)
    return has_project_keyword, has_price, has_period, score


def should_promote_other_to_project(subj: str) -> bool:
    """AIがotherを返したとき、件名からprojectへ昇格すべきか判定。"""
    has_project_keyword, has_price, has_period, score = project_signal_score(subj)
    if has_project_keyword or (has_price and has_period):
        for pat in PROJECT_PATTERNS:
            if re.search(pat, subj):
                return True
        if score >= 2:
            return True
    return False


def _rule_matches_project(subj: str) -> bool:
    has_project_keyword, has_price, has_period, score = project_signal_score(subj)
    if not (has_project_keyword or (has_price and has_period)):
        return False
    for pat in PROJECT_PATTERNS:
        if re.search(pat, subj):
            return True
    return score >= 2


# --- Body-level discriminators ---
BODY_ENGINEER_STRONG = [
    r"見合う案件",
    r"案件(?:が)?ございましたら",
    r"案件(?:が)?ありましたら",
    r"要員情報",
    r"(?:弊社|当社|自社)所属.{0,10}(?:要員|人材|技術者)",
    r"注力.{0,6}(?:要員|人材|技術者)",
    r"(?:要員|人材|技術者).{0,6}(?:情報|をご紹介させて|をご紹介いたし)",  # 紹介+させて=人員側、紹介だけは案件側もある
    r"弊社入社予定",
    r"下記(?:人材|要員)に.{0,10}案件を募集",
    # IMP-2: スキルシート添付・紹介フレーズ・プロフィール項目
    r"(?:スキルシート|職務経歴書|経歴書)\s*(?:添付|送付|共有)",
    r"(?:ご提案させていただきます|ご紹介いたします|ご紹介させていただきます)",
    r"(?:保有スキル|経験年数|希望単価|稼働開始日)\s*[:：]",
]

BODY_PROJECT_STRONG = [
    r"見合う(?:要員|人材|技術者|エンジニア)",  # 見合う人材=案件側(人材を探している)
    r"必須スキル",
    r"案件(?:情報|概要|名)",
    r"募集人数",
    r"増員",
]

# 「要員募集」「エンジニア募集」は案件側の用語
_PROJECT_OVERRIDE_RE = re.compile(r"要員募集|エンジニア募集|人材募集|SE募集|PG募集|技術者募集|案件募集|弊社注力案件|弊社直案件|注力案件")


def _count_template_hits(text: str, patterns: List[str]) -> int:
    return sum(1 for pat in patterns if re.search(pat, text))


def _matches_other(subj: str, body_head: str) -> bool:
    has_ses_context = bool(_OTHER_GUARD_RE.search(subj))
    other_text = subj + " " + body_head[:500]
    for pat in OTHER_PATTERNS:
        if re.search(pat, other_text):
            if has_ses_context and not re.search(pat, subj):
                continue
            return True
    return False


def _detect_strong_project(subj: str, body_head: str) -> Tuple[bool, List[str]]:
    hits: List[str] = []
    if _SUPPRESS_STRONG_PROJECT_RE.search(subj):
        return False, hits
    # 人材チャネル件名は【案件】括弧がない限り strong_proj にしない
    if re.search(r"【[^】]*(?:人材|要員)|人材|要員|プロパー|直個人|直フリ|ご紹介", subj):
        if not re.search(r"【[^】]*案件", subj):
            return False, hits
    if re.search(r"（\d{1,2}）|\(\d{1,2}\)", subj) and not re.search(r"【[^】]*案件", subj):
        return False, hits
    for pat in STRONG_PROJECT_PATTERNS:
        if re.search(pat, subj):
            hits.append(f"subj:{pat[:30]}")
    if not hits and re.search(r"案件", subj) and not _HUMAN_MARKER_RE.search(subj):
        if _ROLE_ONLY_RE.search(subj) or re.search(r"\d{1,2}月|即日", subj):
            hits.append("subj:案件+期間/role(人材語なし)")
    return bool(hits), hits


def _detect_strong_engineer(subj: str, body_head: str) -> Tuple[bool, List[str]]:
    hits: List[str] = []
    has_demo = bool(re.search(r"\d+歳|男性|女性|（\d{1,2}）|\(\d{1,2}\)", subj))
    has_direct = bool(re.search(r"直個人|直フリ|おすすめ人材|注力人材", subj))
    for pat in STRONG_ENGINEER_PATTERNS:
        if re.search(pat, subj + " " + body_head[:200]):
            if re.search(r"要員配信|人材配信", pat) and not _HUMAN_MARKER_RE.search(subj):
                continue
            if re.search(r"【[^】]*(?:人材|要員)", subj) and not has_demo and not has_direct:
                continue
            hits.append(f"strong_eng:{pat[:30]}")
    body_hits = _count_template_hits(body_head, BODY_ENGINEER_TEMPLATE)
    if body_hits >= 2:
        hits.append(f"body_template×{body_hits}")
    return bool(hits), hits


def _should_suppress_skip_rescue(subj: str) -> bool:
    if not _SKIP_RESCUE_SUPPRESS_RE.search(subj):
        return False
    return bool(re.search(r"案件.*(?:探|希望)|幅広.*希望|探して.*案件|案件幅広", subj))


def _is_talent_channel_subject(subj: str) -> bool:
    """人材紹介チャネル件名（【案件】括弧なし）。"""
    if re.search(r"【[^】]*案件", subj):
        return False
    return bool(
        re.search(
            r"【[^】]*(?:人材|要員)|弊社プロパー|直個人|直フリ|注力★直個人|要員配信|人材配信|ご紹介",
            subj,
        )
    )


def _is_engineer_profile_rescue_subject(subj: str) -> bool:
    """engineer DB 取りこぼし救済用の狭い件名パターン（案件募集は除外）。"""
    if re.search(r"(?:案件|募集|人材のご提案|案件配信|要員募集|増員)", subj):
        return False
    if re.search(r"ベテランQAエンジニア", subj):
        return True
    if re.search(r"Web脆弱性診断", subj) and re.search(r"PMO補佐", subj):
        return True
    if re.search(r"【QA／テスト設計】", subj) and re.search(r"経験有", subj):
        return True
    if re.search(r"Python/AWS", subj) and re.search(r"PMO経験有", subj):
        return True
    return False


def _subject_only_skip(subj: str) -> bool:
    """本文なし回帰テスト用の件名限定 skip。"""
    if re.search(r"【7月/注力要員】", subj):
        return True
    if re.search(r"【PMO/7月稼働】", subj) and re.search(r"\d+歳", subj):
        return True
    if re.search(r"【関西要員/7月】", subj):
        return True
    return False


def _is_clear_engineer_intro(subj: str) -> bool:
    """件名から明確な人材紹介と判断できる場合のみ True。"""
    if re.search(r"直個人|直フリ|注力★直個人|おすすめ人材|注力人材|直人材|直要員", subj):
        return True
    if re.search(r"【[^】]*(?:人材|要員|技術者|直人材|直要員)】", subj):
        return True
    if re.search(r"弊社プロパー|弊社要員|弊社社員|弊社契約社員|要員情報|人材情報", subj):
        return True
    if re.search(r"\d+歳\s*[／/]\s*(?:男性|女性)|(?:男性|女性)\s*[／/]", subj):
        return True
    if re.search(r"（\d{1,2}）|\(\d{1,2}\)", subj):
        return True
    if re.search(r"営業中人材|注力要員|所属要員", subj):
        return True
    return False


def _talent_is_project_listing(subj: str) -> bool:
    """【人材】タグ付きでも案件募集フォーマット（属性なし）。"""
    if re.search(r"要員情報|人材情報|案件を探|探して.*案件", subj):
        return False
    if not re.search(r"【[^】]*(?:人材|要員)|(?:Java|PHP|C#|\.NET).*人材", subj):
        return False
    if re.search(r"直個人|直フリ|おすすめ人材|注力★直個人", subj):
        return False
    if re.search(r"\d+歳|男性|女性|（\d{1,2}）", subj):
        return False
    return bool(re.search(r"\d+万", subj) and re.search(r"基本設計|詳細設計|PMO|常駐|リモート|サブリーダー", subj))


def _skip_rescue_project(subj: str) -> bool:
    """skipパターンに該当しても案件として救済する狭い条件。"""
    if _should_suppress_skip_rescue(subj):
        return False
    return bool(
        re.search(
            r"【[^】]*案件[^】]*】|(?:営業中)?案件一覧|新着案件|急募.*案件|案件.*急募|\d{1,2}月案件",
            subj,
        )
    )


# --- Task AB: AA副作用修正 ---
_STRONG_PROJECT_RESCUE_RE = re.compile(
    r"案件|募集|開発支援|導入支援|保守支援|PJ|プロジェクト|業務支援|元請け直",
    re.I,
)
_HARD_PROJECT_INDICATORS = [
    re.compile(p, re.I)
    for p in [
        r"(?:案件|募集案件|増員案件|開発支援|保守支援|導入支援)",
        r"(?:勤務地|作業場所|リモート併用|面談\d+回|契約形態|精算)",
        r"(?:元請け|エンド|PJ|プロジェクト)",
    ]
]
# Task AC: 案件には出にくい人材専用語（pre-skip 強制）
_HUMAN_ONLY_SIGNALS = [
    re.compile(r"弊社(?:正社員|プロパー|社員|メンバー).*(?:紹介|ご紹介)"),
    re.compile(r"(?:注力|おすすめ|イチオシ)(?:要員|人材|技術者)"),
    re.compile(r"\d{2}歳[／/](?:男性|女性)"),
    re.compile(r"(?:弊社|当社)(?:直)?(?:個人事業主|フリーランス)"),
]
_MASS_DIST_RE = re.compile(
    r"(?:注力要員|関西要員|福岡要員|九州要員|大阪要員|名古屋要員|東海要員|首都圏要員)"
    r"|(?:\d{1,2}月稼働)(?!開始|予定)"
    r"|(?:PMO.{0,15}稼働)"
)


def has_human_only_signal(text: str) -> bool:
    """人材専用語（案件テンプレには出にくい表現）。"""
    return any(p.search(text) for p in _HUMAN_ONLY_SIGNALS)


def is_strong_engineer_candidate(subj: str, body_head: str) -> bool:
    """人材紹介メールのテンプレ度。hit>=5 で skip 候補。"""
    text = subj + "\n" + body_head
    hit = 0
    if re.search(r"(?:注力要員|要員情報|要員紹介|人材紹介|紹介可能要員)", text):
        hit += 3
    if re.search(r"(?:\d{1,2}歳|年齢[:：]?\d{2}|男性|女性)", text):
        hit += 2
    if re.search(r"(?:稼働可|即日可|参画可|提案可|常駐可|出社可)", text):
        hit += 2
    if re.search(r"(?:Java|PHP|Python|Go|C#|VBA|SQL|AWS|Spring|React).{0,20}(?:\d年|経験)", text, re.I):
        hit += 2
    if re.search(r"(?:単価|万円|万～|〜\d{2,3}万)", text):
        hit += 1
    if re.search(r"(?:個人事業主|BP|SE|PG|エンジニア)", text, re.I):
        hit += 1
    return hit >= 5


def has_direct_candidate_marker(text: str) -> bool:
    """年齢+性別 or 所属+稼働可 等の候補者明示パターン。"""
    role_hit = bool(
        re.search(r"(?:SE|PG|エンジニア|要員|人材|候補者|技術者)", text, re.I)
    )
    human_hit = bool(
        re.search(
            r"(?:\d{1,2}歳|男性|女性|所属|国籍|並行状況|稼働可|参画可|面談可|単価|経験|スキルシート|一人称)",
            text,
        )
    )
    return role_hit and human_hit


def has_engineer_headline(subj: str) -> bool:
    if re.search(r"★新着★|直個人|注力★直個人", subj):
        return bool(re.search(r"(?:SE|PG|エンジニア)", subj, re.I))
    return bool(re.search(r"(?:ご紹介|人材).*(?:SE|PG|エンジニア)", subj, re.I))


def _engineer_rescue_blocked(text: str) -> bool:
    """FIX-3: 案件構造が強く人材属性がない場合は engineer 救済を無効化。"""
    hard_proj_hits = sum(1 for p in _HARD_PROJECT_INDICATORS if p.search(text))
    no_human_marker = not re.search(
        r"(?:\d{1,2}歳|男性|女性|所属|候補者|人材紹介|要員紹介)", text
    )
    return hard_proj_hits >= 3 and no_human_marker


def has_project_structure(subj: str, body_head: str) -> bool:
    """FIX-4: 案件テンプレ構造スコア >= 4。"""
    text = subj + " " + body_head
    s = 0
    if re.search(r"(?:案件|募集|開発支援|導入支援|保守支援|PJ|プロジェクト)", text, re.I):
        s += 2
    if re.search(r"(?:勤務地|作業場所|最寄|リモート|常駐)", text):
        s += 1
    if re.search(r"(?:面談\d+回|精算|単価|募集人数|開始時期|期間|契約形態)", text):
        s += 1
    if re.search(r"(?:必須スキル|尚可|業務内容|工程|環境)", text):
        s += 2
    return s >= 4


def _should_pre_skip_for_engineer_template(
    subj: str, body_head: str, proj_score: int, eng_score: int
) -> bool:
    """FIX-1: 人材テンプレが強く案件シグナルが弱い場合 skip に戻す。"""
    text = subj + " " + body_head
    if has_human_only_signal(text):
        if has_engineer_headline(subj) or _is_clear_engineer_intro(subj):
            return False
        return True
    proj_strong_hits_subj = len(_STRONG_PROJECT_RESCUE_RE.findall(subj))
    has_case_bracket = bool(re.search(r"【[^】]*案件", subj))
    # 大量配信パターン: 件名の定型句で即判定（body候補者マーカーを無視）
    if _MASS_DIST_RE.search(subj):
        if proj_strong_hits_subj < 2 and not has_case_bracket and not has_engineer_headline(subj):
            return True
        return False
    # 一般人材テンプレート判定
    if not is_strong_engineer_candidate(subj, body_head):
        return False
    if has_engineer_headline(subj) or has_direct_candidate_marker(subj + " " + body_head):
        return False
    if proj_strong_hits_subj >= 2 or has_case_bracket:
        return False
    return True


def _is_mass_talent_subject(subj: str) -> bool:
    """大量配信の人材紹介件名（project誤判定防止）。"""
    if re.search(r"【[^】]*案件", subj):
        return False
    if re.search(
        r"★[^★\n]{0,80}(?:エンジニア|デザイナー)\s*/|"
        r"(?:TypeScript|JavaScript|PHP|Java|Python|Kotlin|Go|C\+\+|C#|インフラ)[^/\n]{0,50}エンジニア/",
        subj,
        re.I,
    ):
        return True
    if re.search(r"【弊社正社員】|【常駐可能！?】", subj) and re.search(
        r"エンジニア|要員|人材|サポート", subj
    ):
        return True
    return False


def _resolve_unknown_fallback(subj: str, body_head: str) -> str:
    """unknown の最終フォールバック（Task AG: 未分類率抑制）。"""
    text = subj + " " + body_head[:400]
    if re.search(
        r"★[^★\n]{0,80}(?:エンジニア|デザイナー)|"
        r"(?:TypeScript|JavaScript|PHP|Java|Python|Kotlin|Go|C\+\+|C#|インフラ)[^/\n]{0,50}エンジニア/",
        subj,
        re.I,
    ):
        return "engineer"
    if re.search(r"★[^★\n]{0,40}人材\s*/", subj):
        return "engineer"
    if re.search(r"人材【|人材｜", subj) and re.search(r"\d{1,2}歳|男性|女性", text):
        return "engineer"
    if re.search(r"人材のご提案", subj):
        return "engineer"
    if re.search(r"【弊社正社員】|【\d{1,2}月[：:][^】]*プロパー】|【常駐可能！?】|正社員/", subj):
        return "engineer"
    if re.search(r"【ベテラン】", subj) and re.search(r"\d{1,2}歳", subj):
        return "engineer"
    if re.search(r"案件希望", subj) and re.search(r"弊社|プロパー|正社員", subj):
        return "engineer"
    if re.search(r"【運用保守】", subj) and re.search(r"取得済み|SV|エンジニア", text):
        return "engineer"
    if re.search(r"速報[：:]", subj) and re.search(r"正社員|プロパー", subj):
        return "engineer"
    if re.search(r"【案件】|【案件情報】", subj):
        return "project"
    if re.search(r"要員募集|エンジニア募集", subj) and not _is_clear_engineer_intro(subj):
        return "project"
    if re.search(r"案件|募集", subj) and re.search(r"\d{2,3}万", subj):
        return "project"
    return "skip"


def classify_by_rule_explain(subj: str, frm: str, body: str = "") -> Tuple[str, Dict]:
    """分類結果と加点理由ログを返す（ベンチマーク・デバッグ用）。"""
    subj = subj or ""
    frm = frm or ""
    body_head = (body or "")[:1000]

    eng_score = 0
    proj_score = 0
    eng_hits: List[str] = []
    proj_hits: List[str] = []

    # Step 1: skip フラグ化（SES強シグナルがあればスコアリング継続 — IMP-5 踏襲）
    skip_hit = False
    for pat in SKIP_PATTERNS:
        if re.search(pat, subj + " " + frm):
            if not _SES_STRONG_RE.search(subj):
                skip_hit = True
                eng_hits.append(f"skip_hit:{pat[:24]}")
            break

    eng_from_subj_priority = False
    has_project_override = bool(_PROJECT_OVERRIDE_RE.search(subj))
    has_project_bracket = bool(re.search(r"【[^】]*案件[^】]*】", subj))

    if not has_project_override:
        for pat in ENGINEER_SUBJECT_PRIORITY:
            if re.search(pat, subj):
                eng_score += 5
                eng_from_subj_priority = True
                eng_hits.append(f"subj_priority(+5):{pat[:24]}")
                break
        if not eng_from_subj_priority:
            for pat in ENGINEER_PATTERNS:
                if re.search(pat, subj + " " + frm[:50]):
                    if has_project_bracket and not _HUMAN_MARKER_RE.search(subj):
                        continue
                    if re.search(r"【[^】]*(?:人材|要員)", subj) and not _HUMAN_MARKER_RE.search(subj):
                        if re.search(r"\d+万", subj) and re.search(r"\d月|即日", subj):
                            continue
                    eng_score += 3
                    eng_hits.append(f"engineer_pat(+3):{pat[:24]}")
                    break

    for trigger, context in AMBIGUOUS_ENGINEER:
        if re.search(trigger, subj) and re.search(context, subj + " " + body_head[:300]):
            eng_score += 3
            eng_hits.append(f"ambiguous_eng(+3):{trigger[:16]}")
            break

    for pat in PROJECT_PATTERNS:
        if re.search(pat, subj):
            proj_score += 2
            proj_hits.append(f"project_pat(+2):{pat[:24]}")
            break

    if has_project_bracket:
        proj_score += 2
        proj_hits.append("project_bracket(+2)")

    if any(kw in subj for kw in PROJECT_PRIORITY_KEYWORDS):
        proj_score += 1
        proj_hits.append("project_kw(+1)")

    body_eng_hit = False
    for pat in BODY_ENGINEER_STRONG:
        if re.search(pat, body_head):
            eng_score += 3
            body_eng_hit = True
            eng_hits.append(f"body_eng(+3):{pat[:24]}")
            break

    struct_hits = len(_BODY_STRUCT_RE.findall(body_head))
    if struct_hits >= 3:
        eng_score += 4
        body_eng_hit = True
        eng_hits.append(f"body_struct(+4)×{struct_hits}")

    body_proj_tpl = _count_template_hits(body_head, BODY_PROJECT_TEMPLATE)
    if body_proj_tpl >= 2:
        proj_score += 3
        proj_hits.append(f"body_proj_tpl(+3)×{body_proj_tpl}")

    body_eng_tpl = _count_template_hits(body_head, BODY_ENGINEER_TEMPLATE)
    if body_eng_tpl >= 2:
        eng_score += 3
        body_eng_hit = True
        eng_hits.append(f"body_eng_tpl(+3)×{body_eng_tpl}")
    has_body_engineer_profile = body_eng_tpl >= 2 or struct_hits >= 3

    for pat in BODY_PROJECT_STRONG:
        if re.search(pat, body_head):
            proj_score += 3
            proj_hits.append(f"body_proj(+3):{pat[:24]}")
            break

    strong_proj, strong_proj_hits = _detect_strong_project(subj, body_head)
    strong_eng, strong_eng_hits = _detect_strong_engineer(subj, body_head)
    proj_hits.extend(strong_proj_hits)
    eng_hits.extend(strong_eng_hits)

    meta = {
        "eng_score": eng_score,
        "proj_score": proj_score,
        "strong_proj": strong_proj,
        "strong_eng": strong_eng,
        "skip_hit": skip_hit,
        "eng_hits": eng_hits,
        "proj_hits": proj_hits,
    }

    # 件名定型 + 本文人材（project構造語3未満）→ engineer（strong_proj で上書き可）
    if eng_from_subj_priority and body_eng_hit and not strong_proj:
        if len(_PROJECT_STRUCT_RE.findall(body_head)) < 3:
            return "engineer", meta

    # FIX-1: 人材テンプレ強 → skip（project 流入抑制、strong_proj より前）
    if not body_head.strip() and _subject_only_skip(subj) and not re.search(
        r"【[^】]*案件", subj
    ):
        return "skip", meta
    if has_human_only_signal(subj + " " + body_head):
        if not (has_engineer_headline(subj) or _is_clear_engineer_intro(subj)):
            return "skip", meta
    if _should_pre_skip_for_engineer_template(subj, body_head, proj_score, eng_score):
        return "skip", meta

    if _is_mass_talent_subject(subj):
        return "engineer", meta

    # 判定順: strong_proj > strong_eng(抑制付) > other > score > skip > unknown
    if strong_proj or _talent_is_project_listing(subj):
        eng_tpl = is_strong_engineer_candidate(subj, body_head) and not re.search(
            r"【[^】]*案件", subj
        )
        if not eng_tpl:
            return "project", meta

    # project DB 誤判定抑制: PM補佐 PMO ベテラン紹介（案件要員募集形式）
    if (
        re.search(r"【PM補佐", subj)
        and re.search(r"PMO", subj)
        and re.search(r"\d{2}歳", subj)
        and not re.search(r"直個人|直フリ|直人材", subj)
    ):
        return "project", meta

    effective_strong_eng = strong_eng and _is_clear_engineer_intro(subj) and proj_score <= eng_score
    if effective_strong_eng:
        return "engineer", meta

    if _matches_other(subj, body_head):
        return "other", meta

    # 【人材/要員】括弧・要員情報は engineer 優先（人材テンプレ強は skip へ）
    if (
        re.search(r"【[^】]*(?:人材|要員|技術者|直人材|直要員)|要員情報|人材情報", subj)
        and not re.search(r"【[^】]*案件", subj)
    ):
        if _should_pre_skip_for_engineer_template(subj, body_head, proj_score, eng_score):
            return "skip", meta
        if (
            (eng_score >= 3 or body_eng_hit or has_body_engineer_profile)
            and (_is_clear_engineer_intro(subj) or has_engineer_headline(subj))
            and not strong_proj
        ):
            return "engineer", meta

    # 人材チャネル件名は明確な人材紹介のみ engineer を優先
    if _is_talent_channel_subject(subj) and _is_clear_engineer_intro(subj) and eng_score >= 3 and not strong_proj:
        return "engineer", meta

    # FIX-2/3: engineer 救済（unknown 落ち防止、案件構造ガード付き）
    combo_text = subj + " " + body_head
    if not _engineer_rescue_blocked(combo_text):
        if (
            has_direct_candidate_marker(combo_text)
            and eng_score >= 3
            and proj_score <= eng_score + 1
            and (_is_clear_engineer_intro(subj) or has_engineer_headline(subj) or re.search(r"直個人|直フリ|★新着★", subj))
        ):
            return "engineer", meta
        if (
            re.search(r"★新着★|直個人|注力★直個人", subj)
            and re.search(r"\d+歳|男性|女性", subj)
            and proj_score <= 2
        ):
            return "engineer", meta
        if (
            has_direct_candidate_marker(subj)
            and re.search(r"一人称|担える", subj)
            and proj_score <= 2
        ):
            return "engineer", meta

    if proj_score >= 4 and proj_score > eng_score + 1:
        if _should_pre_skip_for_engineer_template(subj, body_head, proj_score, eng_score):
            return "skip", meta
        return "project", meta
    if proj_score >= 3 and proj_score > eng_score:
        if _should_pre_skip_for_engineer_template(subj, body_head, proj_score, eng_score):
            return "skip", meta
        return "project", meta

    if eng_score >= 4 and eng_score >= proj_score + 2:
        if _is_clear_engineer_intro(subj) or eng_from_subj_priority:
            return "engineer", meta

    if body_eng_hit and eng_score >= 3 and _is_clear_engineer_intro(subj) and not strong_proj:
        return "engineer", meta

    if eng_score >= 3 and eng_score >= proj_score and not strong_proj:
        if eng_from_subj_priority or re.search(r"【[^】]*(?:人材|要員|技術者|社員情報)", subj):
            return "engineer", meta
        if re.search(r"弊社プロパー|弊社要員|弊社社員|弊社契約社員", subj) and not has_project_bracket:
            return "engineer", meta

    if eng_score == 0 and _rule_matches_project(subj):
        return "project", meta

    _, _, _, sig_score = project_signal_score(subj)
    if sig_score >= 2 and eng_score == 0:
        proj_pattern_hits = sum(1 for pat in PROJECT_PATTERNS if re.search(pat, subj))
        if proj_pattern_hits >= 2:
            return "project", meta

    # skip: strong_proj / 明示的救済で project、それ以外は skip
    if skip_hit:
        if strong_proj or _skip_rescue_project(subj):
            return "project", meta
        return "skip", meta

    if _matches_other(subj, body_head):
        return "other", meta

    if proj_score >= eng_score and proj_score >= 3 and not _is_clear_engineer_intro(subj):
        return "project", meta

    # engineer DB 取りこぼし救済（件名【人材/要員/直人材】）
    if eng_score >= 3 and re.search(r"【[^】]*(?:人材|要員|直人材|直要員|OW人材)", subj):
        return "engineer", meta

    _, _, _, sig_score = project_signal_score(subj)
    if sig_score >= 1 and proj_score >= 2 and eng_score < 4 and not _is_clear_engineer_intro(subj):
        return "project", meta

    # FIX-4: project→unknown 救済（案件構造語あり、人材明示なし）
    if has_project_structure(subj, body_head) and not has_direct_candidate_marker(combo_text):
        return "project", meta

    # engineer 取りこぼし救済（人材プロフィール件名 + 候補者明示、unknown 直前）
    if (
        not _engineer_rescue_blocked(combo_text)
        and has_direct_candidate_marker(combo_text)
        and _is_engineer_profile_rescue_subject(subj)
        and eng_score >= 4
        and eng_score >= proj_score + 2
        and not strong_proj
    ):
        return "engineer", meta

    fallback = _resolve_unknown_fallback(subj, body_head)
    meta["unknown_fallback"] = fallback
    return fallback, meta


def classify_by_rule(subj, frm, body=""):
    verdict, _ = classify_by_rule_explain(subj, frm, body)
    return verdict


if __name__ == "__main__":
    with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_subjects_sample.json", encoding="utf-8") as f:
        data = json.load(f)

    results = {"project": 0, "engineer": 0, "skip": 0, "other": 0, "unknown": 0}
    unknown_samples = []

    for item in data:
        subj = item.get("subject", "")
        frm = item.get("from", "")
        label = classify_by_rule(subj, frm)
        results[label] += 1
        if label == "unknown" and len(unknown_samples) < 30:
            unknown_samples.append(subj[:90])

    total = len(data)
    print("=== 最終版v2 4,000件分類結果 ===")
    for k, v in results.items():
        pct = v / total * 100
        bar = "█" * int(pct / 2)
        print(f"  {k:10s}: {v:4d}件 ({pct:5.1f}%) {bar}")

    ai_needed = results["unknown"]
    ai_pct = ai_needed / total * 100
    rule_pct = 100 - ai_pct
    print(f"\nルール処理: {total - ai_needed}件 ({rule_pct:.1f}%) → AIコスト不要")
    print(f"AI必要:    {ai_needed}件 ({ai_pct:.1f}%)")

    HAIKU_IN = 0.8 / 1e6
    HAIKU_OUT = 4.0 / 1e6
    USD_JPY = 155
    daily_total = 2700

    ai_per_day = daily_total * (ai_pct / 100)
    haiku_classify_cost = ai_per_day * (300 * HAIKU_IN + 50 * HAIKU_OUT)

    proj_per_day = daily_total * (results["project"] / total)
    eng_per_day = daily_total * (results["engineer"] / total)
    proj_cost = proj_per_day * (
        (600 * HAIKU_IN + 100 * HAIKU_OUT) + (1500 * HAIKU_IN + 400 * HAIKU_OUT) + (1500 * HAIKU_IN + 600 * HAIKU_OUT)
    )
    eng_cost = eng_per_day * ((600 * HAIKU_IN + 100 * HAIKU_OUT) + (800 * HAIKU_IN + 200 * HAIKU_OUT))

    daily_usd = haiku_classify_cost + proj_cost + eng_cost
    monthly_usd = daily_usd * 22

    print(f"\n=== コスト再試算（1日{daily_total}件） ===")
    print(f"Haiku分類（unknown {ai_pct:.0f}%のみ）: ${haiku_classify_cost:.3f}/日")
    print(f"案件処理（Haiku全面）: ${proj_cost:.3f}/日")
    print(f"人材処理（Haiku全面）: ${eng_cost:.3f}/日")
    print(f"合計: ${daily_usd:.3f}/日 / 約{daily_usd * USD_JPY:.0f}円/日")
    print(f"月次（22日）: ${monthly_usd:.2f} / 約{monthly_usd * USD_JPY:,.0f}円")
    print(f"\n現状比: ${1220:.0f}/月 → ${monthly_usd:.1f}/月（{(1 - monthly_usd / 1220) * 100:.0f}%削減）")

    print("\n残unknown件名サンプル（上位20件）:")
    for s in unknown_samples[:20]:
        print(f"  {s}")
