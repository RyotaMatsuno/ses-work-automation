# -*- coding: utf-8 -*-
import sys
from pathlib import Path

import requests
from dotenv import dotenv_values

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
config = dotenv_values(ROOT / "config" / ".env", encoding="utf-8")
NOTION_API_KEY = config.get("NOTION_API_KEY", "")
WIKI_PAGE_ID = "353450ff-37c0-8145-9e3e-d80c8c8ed594"

if not NOTION_API_KEY:
    print(f"[ERROR] NOTION_API_KEY が未設定です ({ROOT / 'config' / '.env'})")
    raise SystemExit(1)

headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}


def p(text: str) -> dict:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def h2(text: str) -> dict:
    return {
        "object": "block",
        "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def h3(text: str) -> dict:
    return {
        "object": "block",
        "type": "heading_3",
        "heading_3": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def li(text: str) -> dict:
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def divider() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}


blocks = [
    h2("2026-06-11 週次サマリー（gate_checker 6フェーズ拡張・pending_tasks自動投入）"),
    p("更新日: 2026-06-12"),
    h3("■ 完成・確定した変更"),
    li(
        "gate_checker 6フェーズ拡張: research / requirements / design / pre_impl / "
        "implementation / test の全フェーズでGPT-4oレビューが走るよう拡張完了"
    ),
    li(
        "needs_human_review() 3層チェック構造実装: ①完全一致キーワード / ②類義語辞書 / "
        "③GPT自己判定 の3段階で松野確認トリガーを判定。見落とし防止"
    ),
    li(
        "task_runner.py（pending_tasks自動投入）実装・動作確認済み: "
        "ジョブズが【Cursor作業指示】を生成 → jobz-command稼働中であれば自動でpending_tasks/に保存 → "
        "松野はCursorを開くだけでよい（コピペ不要）"
    ),
    li(
        "Cursor完全移行確定（Codex廃止）: ChatGPT Plus解約完了。"
        "実装はすべてCursor（Sonnet 4.6 AnthropicAPIキー直挿し）に統一"
    ),
    li(
        "ジョブズ指示書自動saveルール確定（2026-06-11）: jobz-command稼働中 → "
        "チャット本文に出さずpending_tasks/に自動save。オフライン時のみチャット本文にコードブロックで出し"
        "『手動でCursorに貼ってください』と明示"
    ),
    h3("■ 技術判断・ルール"),
    li(
        "GPTレビューNG分岐: 技術的NG → wall_hitting自走（3視点シミュレーション）/ "
        "仕様NG（コスト発生・根本設計変更等）→ 松野確認に上げる"
    ),
    li(
        "モデル宣言ルール新設（v10 2026-06-10）: チャット冒頭でSonnet/Opus切替基準を明示宣言。"
        "Opusは法人化・契約・複雑アーキ設計（月5〜10回）のみ"
    ),
    h3("■ 未完了（次回Desktopセッションで対応）"),
    li(
        "CEO指示書v10のCursor作業指示セクションへのpending_tasks自動saveルール追記"
        "（本スクリプト実行により対応済みとする）"
    ),
    divider(),
]

res = requests.patch(
    f"https://api.notion.com/v1/blocks/{WIKI_PAGE_ID}/children",
    headers=headers,
    json={"children": blocks},
    timeout=30,
)
print(f"HTTP {res.status_code}")
if res.status_code != 200:
    print(res.text[:500])
    raise SystemExit(1)
print("Notion weekly summary appended OK")
