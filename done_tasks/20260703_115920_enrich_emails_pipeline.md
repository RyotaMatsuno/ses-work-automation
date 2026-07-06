# 【Cursor作業指示】enrich_emails パイプライン
対象ディレクトリ: ses_work/outreach_system/
参照ファイル: SPEC.md / CLAUDE.md / この指示書
完了条件: 下記全タスク完了 + dry-run成功
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 背景
- master_companies.csv に 26,430社の企業リストを保存済み
- targets.csv にメアドあり 2,613社を投入済み
- 残り約23,800社はメアドなし → HPからメアドを自動取得する必要がある
- ただし全件調査は非効率 → SES/IT企業のみフィルタ後にenrich実行

## データ構成（3層構造）
```
master_companies.csv  (26,430社: TERRA原本)
  ↓ filter_it_ses.py
qualified_companies.csv  (SES/IT企業のみ)
  ↓ enrich_emails.py
targets.csv  (メアドあり or フォームURLあり = 送信可能企業)
```

---

## Task 1: filter_it_ses.py（業種フィルタ）

### 機能
master_companies.csv から SES/IT企業を判定して qualified_companies.csv に出力

### 判定ロジック
#### 肯定キーワード（会社名 or memo列に含まれる）
SES, システム, ソフトウェア, ソフト, IT, DX, Web, 開発, エンジニア, 
インフラ, クラウド, AI, SaaS, 情報, テクノ, データ, ネットワーク,
コンピュータ, コンピューター, プログラム, デジタル, サイバー

#### 否定キーワード（会社名 or memo列に含まれる → 除外）
飲食, 居酒屋, 建設, 不動産, 美容, 歯科, 介護, 製造, 運送, 清掃, 
小売, 農業, 医療, 病院, 保険, 証券, 銀行, 学校, 幼稚園, 保育

#### 判定結果カラム: industry_status
- "include" → qualified_companies.csvに出力
- "exclude" → 除外
- "review" → 一旦includeに含める（後で松野が手動確認可能）

### 出力
- qualified_companies.csv（フィルタ済み企業リスト）
- filter_report.json（include/exclude/review件数レポート）

### 実行
```bash
python outreach_system/filter_it_ses.py --dry-run
python outreach_system/filter_it_ses.py --run
```

---

## Task 2: enrich_emails.py（HP巡回メアド取得）

### 機能
qualified_companies.csv のメアドなし企業について、HPからメアドを自動取得

### 処理フロー
```
企業名 → 企業HPを特定 → HP巡回 → メアド/フォームURL抽出
```

### HP特定方法（優先順位順）
1. master_companies.csvのmemo列にURLがあればそれを使用
2. 企業名から「{企業名} 公式」でGoogle検索（requests + BeautifulSoup）
3. 検索結果の1位がco.jp/or.jp/com等ならHP候補

### 巡回対象ページ（トップ + depth 1）
- トップページ
- /contact, /inquiry, /お問い合わせ
- /company, /about, /会社概要
- /recruit, /採用

### メアド抽出パターン
```python
EMAIL_PATTERNS = [
    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',  # 通常
    r'[a-zA-Z0-9._%+-]+\s*[\[（(]\s*(?:at|AT)\s*[\]）)]\s*[a-zA-Z0-9.-]+\.\w+',  # 難読化
]

# 優先メアドプレフィックス
PRIORITY_PREFIXES = ['info@', 'contact@', 'sales@', 'corp@', 'support@']

# 除外
EXCLUDE_PREFIXES = ['noreply@', 'no-reply@', 'do-not-reply@', 'example@']
```

### フォームURL抽出
- <form>タグのaction属性
- "contact", "inquiry", "お問い合わせ" を含むリンクURL
- Google Forms, HubSpot等の外部フォームURL

### レート制限
- HP巡回: 3秒/サイト（DoS防止）
- Google検索: 20秒/クエリ（ブロック防止）

### シャード分割（phase7d方式）
```bash
python outreach_system/enrich_emails.py --shard-id 0 --shard-count 5 --limit 200 --dry-run
python outreach_system/enrich_emails.py --shard-id 0 --shard-count 5 --limit 200 --run
```

### 状態管理
enrich_state.json に処理状態を保存
```json
{
  "企業名": {
    "status": "done|failed|pending",
    "resolved_url": "https://...",
    "found_email": "info@...",
    "found_form_url": "https://...",
    "attempt_count": 1,
    "last_error": null,
    "updated_at": "2026-07-03T..."
  }
}
```

### 結果反映
enrichで取得したメアドをtargets.csvに追記（重複チェック付き）
```bash
python outreach_system/enrich_emails.py --export-to-targets
```

### 出力
- enrich_state.json（処理状態）
- enrich_report.json（成功/失敗/スキップ件数）

---

## Task 3: import_terra_list.py 更新

既存のimport_terra_list.pyを以下に対応させる:
1. --target master で master_companies.csv に全件出力
2. --target targets で メアドあり企業のみ targets.csv に追記（現在の動作）
3. デフォルトは --target targets（後方互換）

---

## Task 4: SPEC.md 更新

3層構造（master → qualified → targets）を反映
enrich_emails.pyの仕様を追記

---

## Task 5: dry-run検証

1. filter_it_ses.py --dry-run → include/exclude/review件数が妥当か確認
2. enrich_emails.py --shard-id 0 --shard-count 5 --limit 5 --dry-run → 5社分だけテスト
3. 結果をターミナル出力

---

## 技術制約
- jobz-command: 27分タイムアウト → --limit で1回の処理量を制限
- CostGuard: $8/日 → Google検索APIは使わない（スクレイピングのみ）
- requests + BeautifulSoup でHP巡回（Playwrightは不要）
- User-Agent: 一般的なブラウザを偽装
- robots.txt: 確認してdisallowなら巡回スキップ

## 禁止事項
- 本番送信（outreach.py --run）は絶対に実行しない
- master_companies.csv / targets.csv の既存データを削除しない
- LLM API呼び出しはしない（ルールベースのみ）
