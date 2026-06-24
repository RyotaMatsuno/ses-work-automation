# -*- coding: utf-8 -*-
import os
import sys

import requests

sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv

load_dotenv(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")

NOTION_API_KEY = os.environ.get("NOTION_API_KEY", "")
WIKI_PAGE_ID = "353450ff-37c0-8145-9e3e-d80c8c8ed594"  # SESナレッジWiki

headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}


def p(text):
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def h2(text):
    return {
        "object": "block",
        "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def h3(text):
    return {
        "object": "block",
        "type": "heading_3",
        "heading_3": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def li(text):
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def divider():
    return {"object": "block", "type": "divider", "divider": {}}


# 新しいページを作成
page_body = {
    "parent": {"page_id": WIKI_PAGE_ID},
    "properties": {
        "title": {"title": [{"type": "text", "text": {"content": "2026-05-15週 ナレッジまとめ（v12完成・DB大掃除）"}}]}
    },
    "children": [
        h2("✅ 今週完了したこと"),
        h3("1. LINE→メール送信フロー v12完成（Railway内SMTP直接送信）"),
        li("問題: v11まではngrok経由でローカルjobz-commandサーバにコールバックしてSMTP送信していた"),
        li("原因: ngrokがPC起動中しか使えないため、PC落ちるとメール送信が完全に止まる"),
        li("解決: Railway内でsmtplib直接送信に切り替え（ngrok不要化）"),
        li("実装: webhook_server.py の send_email_via_callback をv12に書き換え"),
        li("Railway環境変数追加: SESSALES_MAIL_PASSWORD / MATSUNO_MAIL_PASSWORD / OKAMOTO_MAIL_PASSWORD"),
        li("git push → Railway自動デプロイ → /healthチェック → SMTP送信テスト 全て通過"),
        p(""),
        h3("2. Notion DB大掃除（単価バグ・ステータス・除外対象）"),
        li("単価バグ修正: エンジニア15件・案件7件が円単位で入力されていた（例: 550000→55万）"),
        li("原因: mail_pipeline側のnormalize_priceが円→万変換するが、Notionへの書き込み時に変換前の値が入っていた"),
        li("対処: 全件スキャンして1000以上の値を/10000で修正"),
        li(
            "案件DB: ステータスが全件「募集中」のままでマッチングAIに「稼働中0件」と認識されていた → 全件「稼働中」に変更"
        ),
        li("テスト案件2件（【テスト】Java案件、[テスト]Javaバックエンド）をアーカイブ削除"),
        li("除外対象エンジニア9件を「調整中」に変更してマッチング対象外化"),
        p(""),
        h2("⚠️ 発見した構造的な問題"),
        li("メール自動登録でコンサル・PMO・非エンジニア・外国籍・高単価人材が「稼働可能」で混入している"),
        li("mail_pipelineがスキル・職種を判定せず全員登録するため、除外ルールが機能していない"),
        li("→ 今後の改善候補: mail_pipeline側でAIによる除外フィルタリングを追加する"),
        p(""),
        h2("📋 除外設定した人材一覧（2026-05-15）"),
        li("K.Y: コンサル/DX推進PM/単価180万"),
        li("O.K: PM/PMO・証券業務30年（コンサル系）"),
        li("TK: 上流要件定義中心/単価125万"),
        li("K.D: セールスコンサル/単価100万"),
        li("K.K: PM/PMO/単価94万"),
        li("N.Y: コンテンツマーケ（エンジニア職ではない）"),
        li("王YX（オウ）: 外国籍疑い（除外ルール適用）"),
        li("T.H: ネットワークエンジニア（スキル未登録・マッチ不可）"),
        li("T.T: VBA/Excelマクロのみ（スキルDB不足）"),
        p(""),
        h2("🔧 現在のDB状態（2026-05-15時点）"),
        li("エンジニアDB: 全27件 / 稼働可能18件 / 調整中9件"),
        li("案件DB: 全10件（テスト2件削除後）/ 全件ステータス「稼働中」"),
        li("マッチングAIが使う案件: 10件（PMO案件含む・コンサル案件除外）"),
        p(""),
        h2("🏗️ インフラ状態"),
        li("Railway webhook: https://ses-work-automation-production.up.railway.app （v12稼働中）"),
        li("jobz-command: http://127.0.0.1:8765 （PC起動時自動起動）"),
        li("ses-mail MCP: Claude Desktop経由で松野・岡本・共通アドレスの送受信可能"),
        li("SMTP設定: mail65.onamae.ne.jp:465 SSL / 3アカウント全て動作確認済み"),
        divider(),
        p("作成: ジョブズ（2026-05-15自動生成）"),
    ],
}

res = requests.post("https://api.notion.com/v1/pages", headers=headers, json=page_body)
if res.status_code == 200:
    page = res.json()
    print(f"✓ ページ作成完了: {page['url']}")
else:
    print(f"✗ エラー: {res.status_code} / {res.text[:300]}")
