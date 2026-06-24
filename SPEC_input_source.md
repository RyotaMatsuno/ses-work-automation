# SPEC: 入力元ラベル・所属会社名 追加実装

最終更新: 2026-05-26

## 目的
案件・エンジニアの入力元（どのメール/LINEから来たか）と所属会社名をシステム全体で記録・表示する。
LINEクライアント（レスが早い）からの案件・人材を優先度高として扱えるようにする。

---

## 対象ファイル
1. `mail_pipeline/mail_pipeline.py` — メール入力元ラベル付与・所属名抽出
2. `matching_v2/notify_line.py` — 通知文に入力元・所属名を表示
3. `line_webhook/webhook_server.py` — LINE入力元ラベル付与（松野LINE/岡本LINE）
4. Notion登録時のプロパティ追加（エンジニアDB・案件DB共通）

---

## 入力元ラベル定義

| 入力元 | ラベル値 |
|---|---|
| r-matsuno@terra-ltd.co.jp | 松野メール |
| r-okamoto@terra-ltd.co.jp | 岡本メール |
| sessales@terra-ltd.co.jp | 共通メール |
| 松野公式LINE（webhook） | 松野LINE |
| 岡本公式LINE（webhook） | 岡本LINE |

---

## 所属会社名の取得方法
- メール：本文をClaude AIで解析して抽出。抽出できない場合は空文字。
- LINE：ラベル（松野LINE/岡本LINE）のみ。所属名フィールドは空。

---

## 優先度ロジック
- `松野LINE` or `岡本LINE` → `is_line_source = True`
- マッチング結果のソート: is_line_source=Trueの案件を先頭に
- LINE通知文に `⚡LINE案件` プレフィックスを付与

---

## 変更仕様

### 1. mail_pipeline/mail_pipeline.py

#### (A) メールアドレスから入力元ラベルを判定する関数を追加
```python
def get_input_source_label(email_user: str) -> str:
    """IMAPログインアカウントから入力元ラベルを返す"""
    if "r-matsuno" in email_user:
        return "松野メール"
    elif "r-okamoto" in email_user:
        return "岡本メール"
    else:
        return "共通メール"
```

#### (B) 所属会社名をAIで本文から抽出する関数を追加
```python
def extract_affiliation(body: str) -> str:
    """メール本文から所属会社名を抽出。取れなければ空文字。"""
    # Claude AIに「会社名のみJSON{"company":""}で返せ」と問い合わせ
    # 30文字以内に制限
```

#### (C) register_project() に input_source・affiliation を追加
Notionプロパティ:
- `入力元`: select型 → ラベル値を登録
- `所属会社名`: rich_text型 → 抽出した会社名

#### (D) register_engineer() に同様追加
同じく `入力元` / `所属会社名` を登録

#### (E) main() 内で各メール処理時に input_source を付与
`EMAIL_USER`（ログインアカウント）からラベルを取得して渡す

---

### 2. matching_v2/notify_line.py

#### (A) get_page_info() のproject/engineer情報取得に input_source・affiliation を追加
Notionから取得するフィールドに追加:
- `input_source`: selectプロパティ「入力元」
- `affiliation`: rich_textプロパティ「所属会社名」

#### (B) build_project_message() の表示を修正
案件ブロックに追加:
```
案件: {name}  ⚡LINE案件（input_sourceが*LINEの場合のみ）
所属: {affiliation}（空の場合は表示しない）
入力元: {input_source}
```

エンジニアブロックに追加:
```
▶ {name}
  所属: {affiliation}（空の場合は表示しない）
  入力元: {input_source}
```

#### (C) build_notifications() のソートロジック修正
- project_info.input_sourceが `*LINE` の場合は先頭に来るよう並び替え
（複数案件ある場合のresult.jsonループ順をis_line_sourceでソート）

---

### 3. line_webhook/webhook_server.py

#### (A) ユーザーIDから入力元ラベルを判定
```python
MATSUNO_USER_ID = "Ue3508b43b84991f5a68281da5bf4cf39"
OKAMOTO_USER_ID = "Uac1d23408573586affa37577c4e2b2ab"

def get_line_source_label(user_id: str) -> str:
    if user_id == MATSUNO_USER_ID:
        return "松野LINE"
    elif user_id == OKAMOTO_USER_ID:
        return "岡本LINE"
    else:
        return "松野LINE"  # デフォルト
```

#### (B) Notion登録時（案件DB・エンジニアDB）に `入力元` を付与
register_project_from_line() / register_engineer_from_line() に input_source を渡す

---

## Notion DBプロパティ追加（事前手動作業不要・スクリプトで自動作成）

案件DB・エンジニアDB両方に以下を追加するスクリプト `add_input_source_fields.py` を作成:

| プロパティ名 | 型 | 選択肢 |
|---|---|---|
| 入力元 | select | 松野メール / 岡本メール / 共通メール / 松野LINE / 岡本LINE |
| 所属会社名 | rich_text | - |

---

## 実装チェックリスト → TASKS_input_source.md に記載

---

## 禁止事項
- 既存の処理ロジック（マッチング・ダブルチェック・送信）は変更しない
- Notionプロパティが存在しない場合はスキップ（エラーにしない）
- mail_pipeline.pyのv5バージョン番号をv5.1に上げること
