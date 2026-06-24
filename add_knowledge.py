"""
SESナレッジWiki にナレッジページを追加
2026-05-11週のナレッジまとめ
"""

from pathlib import Path

import requests
from dotenv import dotenv_values

ENV_PATH = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
config = dotenv_values(ENV_PATH)
NOTION_KEY = config.get("NOTION_API_KEY", "")
WIKI_PAGE_ID = "353450ff-37c0-8145-9e3e-d80c8c8ed594"  # SESナレッジWiki

HEADERS = {"Authorization": f"Bearer {NOTION_KEY}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}


def make_paragraph(text):
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def make_heading(text, level=2):
    t = f"heading_{level}"
    return {"object": "block", "type": t, t: {"rich_text": [{"type": "text", "text": {"content": text}}]}}


def make_bullet(text):
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


# ページ作成
page_data = {
    "parent": {"page_id": WIKI_PAGE_ID},
    "properties": {
        "title": {
            "title": [{"type": "text", "text": {"content": "2026-05-11週 ナレッジまとめ（mail_pipeline修正・DB整理）"}}]
        }
    },
    "children": [
        make_heading("概要", 2),
        make_paragraph(
            "mail_pipelineのNotionプロパティ名ミス・日付バリデーション・list返り値エラーを修正。エンジニアDBの旧ゴミデータ問題を発見・クリーンアップ準備完了。"
        ),
        make_heading("■ Notion登録バグと修正内容", 2),
        make_bullet(
            "【v4 → v4.1修正①】register_project の '備考' → '案件詳細' プロパティ名ミス。Notionスキーマと不一致で全案件登録が400エラーになっていた。"
        ),
        make_bullet("【v4 → v4.1修正②】register_project の '必須スキル' → '必要スキル' プロパティ名ミス（同上）。"),
        make_bullet(
            "【v4.1修正③】日付フィールドに '即日'/'来月' 等の日本語が入ると Notion が400 validation_error。is_valid_iso_date() で YYYY-MM-DD 形式のみ通すよう対策。"
        ),
        make_bullet(
            "【v4.1修正④】classify_email() が稀に list を返す場合があり AttributeError。isinstance チェックでガード追加。"
        ),
        make_bullet(
            "【共通】Notion登録失敗時にエラーレスポンス本文をログ出力するよう改修（以前は無音で失敗していた）。"
        ),
        make_heading("■ Notion DBスキーマ（確定版）", 2),
        make_paragraph("案件DB（343450ff-37c0-81e4-934e-f25f90284a3c）"),
        make_bullet(
            "案件名（title）/ 案件詳細（rich_text）/ ステータス（select）/ 必要スキル（multi_select）/ 尚可スキル（multi_select）/ 単価（万円）（number）/ 開始日（date）/ 勤務地（rich_text）/ リモート（select）/ クライアント（rich_text）/ 期間（rich_text）"
        ),
        make_paragraph("エンジニアDB（343450ff-37c0-819d-8769-fb0a8a4ceeb1）"),
        make_bullet(
            "名前（title）/ 稼働状況（select）/ 備考（LINEメモ）（rich_text）/ スキル（multi_select）/ 単価（万円）（number）/ 稼働可能日（date）/ 経験年数（number）/ メール（email）/ 連絡先（phone_number）"
        ),
        make_heading("■ エンジニアDB ゴミデータ問題", 2),
        make_bullet(
            "旧バージョンパイプライン（2026-04-17以前）が暴走し、メール件名がそのままタイトルになったダミーデータが4,643件登録されていた。"
        ),
        make_bullet(
            "正常データ（2026-05-09以降）は10件のみ。cleanup_engineer_db.py（dry_run=True確認済み）を作成。松野CEOの承認後に dry_run=False で実行すれば4,643件を一括削除可能。"
        ),
        make_bullet("削除スクリプト: C:\\Users\\ma_py\\OneDrive\\デスクトップ\\ses_work\\cleanup_engineer_db.py"),
        make_heading("■ パイプライン運用のパターン", 2),
        make_bullet(
            "MCP経由でのpython実行はタイムアウト（120秒超）しやすい。本番実行はsubprocess.Popen でバックグラウンド起動し、ログをpipeline.logに追記する方式が安定。"
        ),
        make_bullet("実行ラッパー: run_pipeline_bg.py で起動 → pipeline.log を確認する2ステップ運用。"),
        make_bullet("タスクスケジューラ（JobzWatchdog）が5分おきに死活監視。command_serverが落ちていれば自動再起動。"),
        make_heading("■ 判断マニュアル変更（2026-05-01）", 2),
        make_bullet("PMO案件は提案対象に含める。除外はコンサル案件のみ（旧：PM/コンサル両方除外）。"),
        make_heading("■ TODO（松野CEO確認待ち）", 2),
        make_bullet("エンジニアDB旧データ4,643件の一括削除 → cleanup_engineer_db.py の dry_run=False で実行"),
        make_bullet("岡本Webhook URL設定 → 岡本から連絡待ち。完了後にLINEパイプラインのend-to-endテスト実施。"),
    ],
}

r = requests.post("https://api.notion.com/v1/pages", headers=HEADERS, json=page_data)
print(f"ナレッジページ作成: {r.status_code}")
if r.status_code == 200:
    page = r.json()
    print(f"URL: {page.get('url', '')}")
else:
    print(r.text[:300])
