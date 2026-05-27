# SPEC.md — アウトリーチリスト収集スクリプト

最終更新: 2026-05-26

## 概要
IT・SES企業のコンタクト情報をGoogleスクレイピングで収集し、
outreach_system/targets.csvに追記する`collect_targets.py`を作成する。

## 収集方法
以下の検索クエリをrequests+BeautifulSoupで処理する：

### クエリ一覧（各クエリで上位5件のドメインを取得）
1. `SES企業 東京 メールアドレス site:*.co.jp`
2. `SIer 東京 採用 contact site:*.co.jp`
3. `システム開発 受託 東京 問い合わせ site:*.co.jp`
4. `SES派遣 IT企業 関東 mail`
5. `フリーランスエンジニア 紹介 SES 東京`

### Googleスクレイピング仕様
- URL: `https://www.google.co.jp/search?q={query}&num=10&hl=ja`
- 検索結果からドメイン一覧を抽出
- 各ドメインのトップページまたは/contactページにアクセス
- ページ内からemailアドレスを正規表現で抽出: `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}`
- 個人ドメイン（gmail.com、yahoo.co.jp等）は除外

### 会社種別判定
- URLやページ内テキストに「SES」「派遣」「技術者派遣」→ type='ses'
- それ以外 → type='prime'

## 出力
- `outreach_system/targets.csv`に追記（既存の会社はスキップ）
- `outreach_system/collect_log.json`に収集ログを保存

## ファイル構成
- `outreach_system/collect_targets.py`（新規作成）

## 完了条件
1. py_compile collect_targets.py エラーなし
2. python collect_targets.py --dry-run で収集結果プレビュー（CSV書き込みなし）
3. --dry-runで1件以上の候補が出力されること
