# SPEC.md — Phase1営業パイプライン

最終更新: 2026-05-25

## 目的
メールで届いた案件情報を元に、NotionエンジニアDBからマッチング候補を抽出し、
所属向け意向確認メール（テンプレート1）の下書きを自動生成してLINEに通知する。
松野・岡本がLINEで確認→承認→メール送信、という営業フローを自動化する。

## システム構成

```
pipeline.py（メイン）
  ├─ Step1: Notion案件DBから「募集中」案件を取得
  ├─ Step2: Notion エンジニアDBから稼働可能エンジニアを取得
  ├─ Step3: マッチング（既存matching_v2/matching_v2.pyのロジックを参考に）
  └─ Step4: 意向確認メール文生成（テンプレート1ベース）
       └─ result.json に出力
```

## ファイル構成
```
pipeline_v1/
├── CLAUDE.md
├── SPEC.md
├── TASKS.md
├── pipeline.py        # メインスクリプト
├── fetcher.py         # Notion DB取得
├── matcher.py         # マッチングロジック
├── composer.py        # メール文生成
└── result_pipeline.json  # 出力（dry_run時の確認用）
```

## Step1: 案件取得（fetcher.py）
- Notion案件DB（343450ff-37c0-81e4-934e-f25f90284a3c）をqueryする
- フィルタ: ステータス=「募集中」
- 取得フィールド: 案件名, 必要スキル, 尚可スキル, 単価(万円), 勤務地, 期間, 案件詳細, 担当者
- 情報鮮度チェック: created_time が4営業日以内のもののみ対象

## Step2: エンジニア取得（fetcher.py）
- Notionエンジニアdb（343450ff-37c0-819d-8769-fb0a8a4ceeb1）をqueryする
- フィルタ: 稼働状況=「稼働可能」
- 取得フィールド: 名前, スキル, 単価(万円), 経験年数, 担当者, 備考(LINEメモ)
- 鮮度チェック: created_time が3週間以内のもののみ対象（判断マニュアルv3ルール）

## Step3: マッチング（matcher.py）
### 除外ルール（判断マニュアルv3準拠）
- 必須スキルに1つでも×がある場合 → 提案対象外
- 単価乖離が5万超（プロジェクト単価 - エンジニア単価 < 5万 or > 5万乖離） → 除外
- 粗利最低5万確保できないものは除外

### スコアリング
- 必須スキル全○: 基準点
- 尚可スキル○率: 高いほどスコアUP
- 粗利: 7万以上=最高評価, 5万=最低合格

### 出力
- 案件ごとに上位3名を候補リストとして返す
- 候補が0名の案件はスキップ

## Step4: 意向確認メール文生成（composer.py）
- 提案テンプレート集v1のテンプレート1を使用
- テンプレート変数を埋める:
  - {案件名}, {業務内容}, {必須スキル}, {尚可スキル}
  - {提案単価}: 粗利7万目標の単価を計算して入力
  - {期間}, {勤務地}, {リモート}, {面談回数}, {外国籍可否}
  - 必須スキルの○×フォームも自動生成
- dry_run=Trueのとき: result_pipeline.jsonに書き出すだけ（メール送信しない）

## テンプレート1（参考）
```
件名: ◯◯様 案件ご検討のお願い（{職種・エリア}）

{所属会社名} {担当者名}様

いつもお世話になっております。
人員のご紹介ありがとうございます。
下記案件いかがでしょうか。

▼必須スキル（○/×）
 □ {必須スキル1}：
 □ {必須スキル2}：
▼尚可スキル（○/×）
 □ {尚可スキル1}：

▼並行状況
 例）なし

何卒よろしくお願いいたします。
```

## 出力形式（result_pipeline.json）
```json
{
  "generated_at": "2026-05-25T09:00:00",
  "total_projects": 3,
  "matched_projects": 2,
  "items": [
    {
      "project": {"name": "案件名", "price": 65, "required_skills": ["Java"]},
      "candidates": [
        {
          "name": "山田太郎",
          "price": 58,
          "gross_profit": 7,
          "required_match": {"Java": true},
          "optional_match": {},
          "draft_mail": "件名: ...\n\n本文..."
        }
      ]
    }
  ]
}
```

## dry_run引数
```bash
python pipeline.py --dry-run      # 出力のみ（デフォルト）
python pipeline.py --run          # 将来的に送信まで行う
```

## credentialロード方法
```python
from dotenv import dotenv_values
ENV_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env"
config = dotenv_values(ENV_PATH)
NOTION_API_KEY = config["NOTION_API_KEY"]
```
