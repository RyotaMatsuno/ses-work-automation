# Phase 9 APIトークン申請ガイド（松野さん作業）

Phase 9 の公式API取得には、以下2つのトークン申請が必要です。  
いずれも**無料**ですが、**メール確認**が必要なため松野さんのメールアドレスでの登録をお願いします。

トークン取得後は `config/.env` に追記し、Cursor または PowerShell から Phase 9 パイプラインを実行します。

---

## Phase 9A: gBizINFO API（経済産業省）

### 申請URL

| 用途 | URL |
|------|-----|
| 利用申請（ここから開始） | https://info.gbiz.go.jp/index.html → 「REST APIを利用する」→ 利用申請 |
| API説明 | https://content.info.gbiz.go.jp/api/index.html |
| Swagger UI（トークン取得後の動作確認） | https://info.gbiz.go.jp/hojin/swagger-ui/index.html |

### 手順

1. https://info.gbiz.go.jp/index.html を開く
2. 「REST APIを利用する」→「利用申請」をクリック
3. 利用目的（例: SES企業調査・法人情報の社内分析）と連絡先メール（**松野さんのメール**）を入力して送信
4. 登録メールに「Web API 利用申請完了」が届く（数分〜数時間）
5. メール内URLを開き、**APIトークン**をコピー
6. 以下のファイルを開き、コメント行を外してトークンを設定:

```
C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env
```

```
GBIZ_API_TOKEN=（取得したトークン）
```

### 取得データの条件（スクリプトが自動実行）

- 業種: 情報通信業相当（`business_item=情報処理`）
- 所在地: 東京都・神奈川県・埼玉県・千葉県・愛知県
- 商号: 「システム」「ソフト」「テクノロジー」「ソリューション」「IT」を含む法人

### 取得後の実行コマンド

```powershell
cd "C:\Users\ma_py\OneDrive\デスクトップ\ses_work\research_results"
python crawl_phase9a_gbiz.py
```

出力: `phase9a_gbiz_companies.csv`

---

## Phase 9B: 国税庁法人番号API

### 申請URL

| 用途 | URL |
|------|-----|
| Web-API概要 | https://www.houjin-bangou.nta.go.jp/webapi/ |
| **仮登録（ここから開始）** | https://www.invoice-kohyo.nta.go.jp/web-api/pre-reg/ |

※ 法人番号公表サイトの Web-API ページからも同じ仮登録フォームへ誘導されます。

### 手順

1. 仮登録画面（上記URL）に**松野さんのメールアドレス**を入力して送信
2. 届いたメールのURLから「アプリケーションID発行届出フォーム」を開く
3. 利用者情報（法人名・担当者・電話番号・利用目的等）を入力して本申請
4. **数日後**（早い場合は当日）、メールで13桁のアプリケーションIDが届く
5. `.env` に追記:

```
NTA_APP_ID=（13桁のアプリケーションID）
```

### 取得データの条件（スクリプトが自動実行）

- 商号部分一致検索: `システムエンジニアリング` / `システム開発` / `ソフトウェア` / `SES` / `技術者派遣`
- 取得後、SES/IT系商号のみフィルタ

### 取得後の実行コマンド

```powershell
python crawl_phase9b_nta.py
```

出力: `phase9b_nta_companies.csv`

---

## Phase 9C: 統合・スクリーニング（トークン取得後）

```powershell
cd "C:\Users\ma_py\OneDrive\デスクトップ\ses_work\research_results"

# 名寄せ → 新規企業抽出
python merge_phase9.py

# Bingスクリーニング（5並列・20秒レート制限・1日500社上限）
python run_phase9c_parallel.py --total 5 --rate-limit 20 --daily-limit 500

# サマリー生成
python write_phase9_summary.py
```

または一括:

```powershell
python run_phase9_all.py
```

### スクリーニング方式（Phase 7D 改良版・2段階）

1. `"{会社名}" SES` でSES企業かどうかを判定
2. SES=yes の企業のみ `"{会社名}" "営業" "粗利" OR "インセンティブ" OR "還元"` でインセンティブ検索

---

## トークン設定確認

```powershell
cd "C:\Users\ma_py\OneDrive\デスクトップ\ses_work\research_results"
python -c "from phase9_helpers import gbiz_token, nta_app_id; print('GBIZ:', 'OK' if gbiz_token() else '未設定'); print('NTA:', 'OK' if nta_app_id() else '未設定')"
```

両方「OK」になったら `python run_phase9_all.py` で全工程を実行できます。

---

## 注意事項

- gBizINFO API: ヘッダー `X-hojinInfo-api-token` にトークンを設定（スクリプトが自動処理）
- 国税庁API: 商号検索は部分一致（mode=2）、2000件超は分割取得（divideパラメータ）
- Bingスクリーニングは1日500社上限。大量の新規企業がある場合は複数日に分けて実行
- 出力先: `C:\Users\ma_py\OneDrive\デスクトップ\ses_work\research_results\`
