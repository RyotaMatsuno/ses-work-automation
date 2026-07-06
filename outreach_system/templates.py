from __future__ import annotations

from send_mail import OUTREACH_FROM_EMAIL, SENDER_COMPANY, SENDER_NAME


def get_template(template_type: str, contact_name: str) -> tuple[str, str]:
    """
    Returns (subject, body) for the given template_type.
    template_type: "unified" | "project" | "engineer"
    """
    name = contact_name or "ご担当者"
    sender = SENDER_NAME or "深谷"
    company = SENDER_COMPANY or "株式会社TERRA"
    email = OUTREACH_FROM_EMAIL

    if template_type == "project":
        subject = f"エンジニアのご提案について／{company}"
        body = f"""{name}様

突然のご連絡失礼いたします。
{company} {sender}と申します。

弊社はSESエンジニアのご提案を行っており、
貴社のエンジニアリソース確保のお力になれればと思い
ご連絡させていただきました。

■ ご提案可能なスキル帯
・Java / Python / PHP 等のWeb系開発
・AWS / Azure 等のインフラ・クラウド基盤
・PMO / 上流工程経験者

即日〜翌月稼働可能な人員を常時抱えております。
エンジニアをお探しの際は、お気軽にご返信いただければ幸いです。

何卒よろしくお願いいたします。

━━━━━━━━━━━━━━━━
{company}
{sender}
Email: {email}
━━━━━━━━━━━━━━━━
"""
        return subject, body

    if template_type == "engineer":
        subject = f"BP提携・案件情報のご相談／{company}"
        body = f"""{name}様

突然のご連絡失礼いたします。
{company} {sender}と申します。

弊社はSES事業を展開しており、
常時複数の案件情報を保有しております。

貴社にてフリー予定のエンジニア様がいらっしゃいましたら、
ぜひご紹介いただければ幸いです。
案件内容に応じて柔軟にご提案させていただきます。

ご興味がございましたら、お気軽にご返信ください。

何卒よろしくお願いいたします。

━━━━━━━━━━━━━━━━
{company}
{sender}
Email: {email}
━━━━━━━━━━━━━━━━
"""
        return subject, body

    # unified（デフォルト）
    subject = f"案件・人員の情報交換のご相談／{company}"
    body = f"""{name}様

突然のご連絡失礼いたします。
{company} {sender}と申します。

弊社はSES事業を展開しており、
案件情報・人員情報の交換を積極的に行っております。

貴社にてエンジニアをお探しの際はご提案が可能ですし、
案件をお持ちの際はぜひご紹介いただければ幸いです。

まずは情報交換からでも構いませんので、
ご興味がございましたらお気軽にご返信ください。

何卒よろしくお願いいたします。

━━━━━━━━━━━━━━━━
{company}
{sender}
Email: {email}
━━━━━━━━━━━━━━━━
"""
    return subject, body
