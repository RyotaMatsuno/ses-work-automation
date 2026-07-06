【Cursor作業指示】
対象ディレクトリ: ses_work/
作業内容: 「選考中」ステータスをコードベースから完全除去
参照ファイル: CLAUDE.md
完了条件: 本番コードに「選考中」への参照ゼロ + 動作確認

## 背景
CEO判断: 案件DBのステータスを「募集中」「終了」「営業終了」の3つに統一。
「選考中」は562件全て「終了」に変更済み。コード側から残存参照を除去する。

## 修正対象（本番コードのみ）

### 1. matching_v3/notion_client.py (L153付近)
ステータスを「選考中」にセットしている箇所を削除。
- ステータスを変更する処理自体を削除（募集中のまま維持）
- 新規作成時は「募集中」をセット

### 2. line_webhook/webhook_server.py (L1084, 1091, 1308, 1411)
選考中を含むORフィルタから「選考中」を削除。
例:
BEFORE:
  {"or": [
    {"property": "ステータス", "select": {"equals": "募集中"}},
    {"property": "ステータス", "select": {"equals": "選考中"}}
  ]}
AFTER:
  {"property": "ステータス", "select": {"equals": "募集中"}}

※ ORフィルタが募集中のみになる場合、orラッパーを外して単一フィルタに簡略化する。

### 3. daily_report.py (L29)
BEFORE: ACTIVE_STATUSES = ("募集中", "選考中")
AFTER:  ACTIVE_STATUSES = ("募集中",)

### 4. check_case_count.py / check_status.py
ステータスリストから「選考中」を削除。

### 5. notion/create_databases.py (L96)
DB定義から選考中のselect optionを削除:
BEFORE: {"name": "選考中", "color": "yellow"},
AFTER:  (行削除)

## やらなくていいこと
- _archive_tmp/ 内のファイル → 触らない
- research_results/ 内のファイル → 触らない
- write_*_spec.py → ドキュメントなので触らない
- Notionのselect option削除 → API制限あり、手動でやる

## テスト
1. grep -r "選考中" で本番コード（上記5ファイル以外）に残存がないこと
2. matching_v3 dry-run: 募集中案件を正常取得できること
3. webhook_server: フィルタが正常動作すること（ステータス=募集中のみ返ること）
4. daily_report: ACTIVE_STATUSESが1要素のtupleで正常動作すること

## 禁止事項
- 「選考中」を「終了」に置換する処理を新たに追加しない（もう不要）
- 既存の募集中/終了/営業終了のロジックを変更しない

## 完了条件チェックリスト
- [x] notion_client.py: 選考中セット処理を削除
- [x] webhook_server.py: 4箇所のフィルタ修正
- [x] daily_report.py: ACTIVE_STATUSES修正
- [x] check_case_count.py / check_status.py: 修正
- [x] create_databases.py: select option削除
- [x] 本番コードに「選考中」参照が0であること（grepで確認）
