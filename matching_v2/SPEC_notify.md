# SPEC_notify.md - 担当者別LINE通知機能

最終更新: 2026-05-22

## 目的
matching_v2のresult.jsonを読み、案件・エンジニアの担当者カラムを参照して
担当者別にLINE Push通知を送る。

## 入力
- matching_v2/result.json（matching_v2.pyが生成）
- Notion エンジニアDB: 343450ff-37c0-819d-8769-fb0a8a4ceeb1
- Notion 案件DB: 343450ff-37c0-81e4-934e-f25f90284a3c
- 環境変数: config/.env

## 環境変数（参照のみ、変更しない）
- LINE_CHANNEL_ACCESS_TOKEN: 松野公式LINEのアクセストークン
- MATSUNO_LINE_USER_ID: 松野のLINEユーザーID
- OKAMOTO_LINE_CHANNEL_ACCESS_TOKEN: 岡本公式LINEのアクセストークン
- OKAMOTO_LINE_USER_ID: 岡本のLINEユーザーID
- NOTION_API_KEY

## 出力ファイル
matching_v2/notify_line.py（新規作成）

## 担当者取得ロジック
- Notionの案件/エンジニア各レコードに「担当者」セレクトカラムあり
- 値: "松野" / "岡本" / "共通" / None（未設定）
- Noneまたは"共通"は「松野担当」として扱う（デフォルト）

## 通知ロジック（4ケース）

### ケース1: 松野案件 × 松野エンジニア
- 松野LINEに通知: マッチ結果 + 「意向確認をお願いします」

### ケース2: 岡本案件 × 岡本エンジニア
- 岡本LINEに通知: マッチ結果 + 「意向確認をお願いします」

### ケース3: 松野案件 × 岡本エンジニア（クロス）
- 松野LINEに通知: 「{エンジニア名}は岡本担当のエンジニアです。岡本に意向確認を依頼しました」
- 岡本LINEに通知: 「{案件名}（松野担当案件）に{エンジニア名}がマッチしました。意向確認をお願いします」

### ケース4: 岡本案件 × 松野エンジニア（クロス）
- 岡本LINEに通知: 「{エンジニア名}は松野担当のエンジニアです。松野に意向確認を依頼しました」
- 松野LINEに通知: 「{案件名}（岡本担当案件）に{エンジニア名}がマッチしました。意向確認をお願いします」

## LINE Push通知の実装方法
```python
import requests

def push_message(channel_token: str, user_id: str, text: str):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {channel_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "to": user_id,
        "messages": [{"type": "text", "text": text}]
    }
    r = requests.post(url, headers=headers, json=payload, timeout=10)
    return r.status_code, r.text
```

## 通知メッセージのフォーマット

### 通常通知（自担当）
```
【マッチング結果】
案件: {案件名}
──────────────
▶ {エンジニア名}（スコア: {score}）
  単価: {price}万円 / 稼働: {available_date}
  必須: {required_skills判定}
  尚可: {optional_skills判定}

意向確認をお願いします。
```

### クロス通知（案件担当者宛）
```
【マッチング結果】
案件: {案件名}
──────────────
▶ {エンジニア名}（スコア: {score}）
  単価: {price}万円 / 稼働: {available_date}
  ※{相手担当者名}担当エンジニアのため、意向確認を依頼しました。
```

### クロス通知（エンジニア担当者宛）
```
【意向確認依頼】
{案件名}（{案件担当者名}担当案件）に
{エンジニア名}がマッチしました。

意向確認をお願いします。
スコア: {score} / 単価: {price}万円
```

## result.jsonのフォーマット（参照）
```json
[
  {
    "project": {
      "id": "notion_page_id",
      "name": "案件名",
      "price": 65
    },
    "candidates": [
      {
        "name": "エンジニア名",
        "id": "notion_page_id",
        "score": 0.95,
        "price": 65,
        "available_date": "2026-06-01",
        "required_judgement": {"Java": "◯", "Spring": "◯"},
        "optional_judgement": {"AWS": "◯"}
      }
    ]
  }
]
```

## 担当者取得の実装
result.jsonにはNotionのpage_idが入っている。
Notionから担当者を取得する関数を実装すること。

```python
def get_assignee(page_id: str, headers: dict) -> str:
    """NotionページのIDから担当者を取得。未設定・共通はデフォルト'松野'を返す"""
    r = requests.get(f"https://api.notion.com/v1/pages/{page_id}", headers=headers, timeout=10)
    props = r.json().get("properties", {})
    s = props.get("担当者", {}).get("select")
    name = s["name"] if s else None
    if name in ("岡本",):
        return "岡本"
    return "松野"  # デフォルト
```

## ファイル構成
matching_v2/
├── notify_line.py  # 今回作成するファイル
└── ...（既存ファイルは変更しない）

## Acceptance（完了条件）
- [ ] python matching_v2/notify_line.py --dry-run でLINE送信せずに通知内容をコンソール出力
- [ ] --dry-run なしで実際にLINE Push送信
- [ ] クロス案件で両者に通知が届く
- [ ] 構文エラーなし（py_compile通過）
- [ ] result.jsonが空（candidates:[]）の案件はスキップ

## 注意事項
- 既存ファイルは変更しない（matching_v2.py, skill_judge.py等）
- config/.envは変更しない
- LINE送信はpush_messageのみ使用（reply不要）
- --dry-runフラグを必ず実装（誤送信防止）
- Notionへの書き込みは不要（読み取りのみ）
