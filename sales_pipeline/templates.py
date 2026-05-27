from __future__ import annotations


IKOUKAKUNIN_SUBJECT = "{candidate_name}様 案件ご検討のお願い（{role_area}）"

IKOUKAKUNIN_TEMPLATE = """{affiliation} {contact_name}様

いつもお世話になっております。

人員のご紹介ありがとうございます。
下記案件いかがでしょうか。
ご検討いただけますと幸いです。

また、エントリーいただける場合下記2点ご教授いただけますと幸いです。
・並行状況
・必須、尚可の○×

━━━━━━━━━━━━━━━━━━
■ 案件概要
━━━━━━━━━━━━━━━━━━
案件名    : {project_name}
業務内容  : {description}
必須スキル: {required_skills}
尚可スキル: {preferred_skills}
単価      : {proposed_price}万円
期間      : {period}
勤務地    : {location}（リモート可否: {remote}）
面談      : {interview_count}回
外国籍    : {foreign_ok}

━━━━━━━━━━━━━━━━━━
■ ご記入フォーマット
━━━━━━━━━━━━━━━━━━
▼必須スキル（○/×）
{required_format}
▼尚可スキル（○/×）
{preferred_format}

▼並行状況
 例）
  ・A社: 面談調整中
  ・B社: 面談予定 2/2（○月○日）
  ・C社: 結果待ち 2/2（面談実施日 ○月○日）

何卒よろしくお願いいたします。
"""

PROPOSAL_SUBJECT = "{project_name} ご提案"

PROPOSAL_TEMPLATE = """ご担当者様

いつもお世話になっております。
下記の通り、候補者をご提案いたします。

━━━━━━━━━━━━━━━━━━
■ 案件
━━━━━━━━━━━━━━━━━━
{project_name}

━━━━━━━━━━━━━━━━━━
■ ご提案候補者
━━━━━━━━━━━━━━━━━━
{candidate_blocks}

━━━━━━━━━━━━━━━━━━
■ サマリー
━━━━━━━━━━━━━━━━━━
{summary}

ご確認のほど、何卒よろしくお願いいたします。
"""

CANDIDATE_TEMPLATE = """【{rank_label}】{name}
単価: {price}万円
稼働開始: {available_date}
必須スキル: {required}
尚可スキル: {preferred}
補足: {appeal}
"""


def skill_format(skills: list[str]) -> str:
    if not skills:
        return "・特になし"
    return "\n".join(f"・{skill}: " for skill in skills)
