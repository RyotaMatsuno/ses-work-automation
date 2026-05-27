# CLAUDE.md — アウトリーチリスト収集スクリプト

## 役割
IT・SES企業のメールアドレスをネット検索で収集し、outreach_system/targets.csvに追記する。

## 禁止事項
- 既存のtargets.csvを上書きしない（追記のみ）
- 重複社名はスキップする
- スクレイピングで個人情報（個人メール等）を収集しない
- requestsのUser-Agentは'Mozilla/5.0'を使用する

## 収集対象
- IT企業（システム開発・SES・受託開発）
- メールアドレスが取得できる会社のみ
- 関東圏の企業を優先（東京・神奈川・埼玉・千葉）

## 出力フォーマット
targets.csvのカラム: company, contact_name, email, type, memo
- type: 'ses'（SES/SIer）または 'prime'（元請け）
- contact_name: 不明な場合は空文字
- memo: 収集元URL

## コーディングルール
- Python 3.11
- requests + BeautifulSoup4使用
- 1リクエストごとにtime.sleep(1)以上入れる
- エラーは握りつぶさずprint出力
- 収集完了後に「追加X社 / スキップY社（重複）」をprint
