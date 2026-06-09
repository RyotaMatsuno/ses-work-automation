# SPEC.md - 提案対象フラグ自動判定システム

バージョン: 1.0
作成日: 2026-06-09

## 1. 目的

Notionエンジニアデータベースの全エンジニアに対して、
判断マニュアルv3 §1の除外ルールをルールベースで自動判定し、
「提案対象フラグ」（checkbox）と「除外理由」（text）を自動更新する。

## 2. 実行タイミング

- matching_v3の毎日8:00自動実行の前に実行（前処理として組み込む）
- 単体実行も可能（python run_flag_updater.py）

## 3. 処理フロー

Step 0: エンジニアDBのプロパティ一覧を取得・検査
Step 1: 必要なプロパティが存在しなければ自動作成
Step 2: エンジニア全件取得（ページネーション対応）
Step 3: 各エンジニアに除外ルール判定を実行
Step 4: 結果をNotionに一括更新（フラグ + 除外理由）
Step 5: 結果サマリーをログ出力

## 4. Notionプロパティ管理

実行時にDBスキーマを取得し、以下が存在しなければ自動でPATCH /databases/{id} して追加する。

| プロパティ名     | 型         | 用途                                       |
|----------------|------------|------------------------------------------|
| 提案対象フラグ   | checkbox   | True=提案可、False=除外                    |
| 除外理由        | rich_text  | 除外時の理由（複数ある場合は改行区切り）        |
| 国籍           | select     | 外国籍判定用                               |
| 居住地         | select     | 地方人材判定用                             |
| 稼働終了日      | date       | ブランク判定用                             |
| 短期連続フラグ  | checkbox   | 短期案件連続の手動入力用                     |
| 既往歴フラグ    | checkbox   | 既往歴の手動入力用                          |

※ 既存プロパティは変更しない。存在チェックして追加のみ。

## 5. 除外ルール判定ロジック

### 5-1. 外国籍
- 国籍プロパティが未入力（None/空）の場合は除外しない（安全側）
- 「日本」以外の値が入力されている場合のみ除外
- reasons.append("外国籍")

### 5-2. 地方人材
KANTO_PREFECTURES = ["東京", "神奈川", "埼玉", "千葉", "茨城", "栃木", "群馬"]
- 居住地未入力の場合は除外しない（安全側）
- 関東7都県以外が入力されている場合に除外
- reasons.append(f"地方人材: {residence}")

### 5-3. ブランク（稼働終了から365日超）
BLANK_DAYS_THRESHOLD = 365
- 稼働終了日未入力の場合は除外しない（現在稼働中とみなす）
- reasons.append(f"ブランク{days_blank}日")

### 5-4. 短期案件連続
- 短期連続フラグ == True の場合に除外
- reasons.append("短期案件連続")

### 5-5. 既往歴
- 既往歴フラグ == True の場合に除外
- reasons.append("既往歴")

## 6. Notion更新仕様

エンドポイント: PATCH /v1/pages/{page_id}
- 提案対象フラグ: checkbox（True/False）
- 除外理由: rich_text（複数理由は"\n"区切り、True時は空文字でクリア）

## 7. レート制限対策
- PATCH後に time.sleep(0.4) を挿入
- 100件超える場合は10件ごとにsleep(1)を追加

## 8. ログ仕様
- ファイル: logs/flag_updater_YYYYMMDD.log
- コンソールにも同時出力
- サマリー: 総件数/対象件数/除外件数/除外者氏名と理由一覧

## 9. matching_v3との統合
matching_v3/matching_v3.py の冒頭に追加:
  import sys, os
  sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
  from flag_auto_updater.run_flag_updater import run_flag_updater
  run_flag_updater()

## 10. エラーハンドリング
- Notion API 401: ERROR出力して処理中断
- Notion API 429: exponential backoff（最大3回リトライ）
- プロパティ追加失敗: WARNING出力、既存データで処理続行
- 個別ページ更新失敗: WARNING出力して次のページに続行

## 11. 設定値（定数）
ENGINEER_DB_ID = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"
BLANK_DAYS_THRESHOLD = 365
KANTO_PREFECTURES = ["東京", "神奈川", "埼玉", "千葉", "茨城", "栃木", "群馬"]
NOTION_API_VERSION = "2022-06-28"
RATE_LIMIT_SLEEP = 0.4
