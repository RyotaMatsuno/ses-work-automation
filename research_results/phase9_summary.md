# Phase 9 SES企業マスター拡大 サマリー

生成日: 2026-07-07

## 概要
- 既存マスター（Phase 7）: **1632** 社
- Phase 9A（gBizINFO）取得: **0** 社
- Phase 9B（国税庁API）取得: **0** 社
- 新規追加企業（名寄せ後）: **0** 社
- 拡張後マスター総数（推定）: **1632** 社
- 推定母集団（10,000社）に対する網羅率: **16.3%**

## Bingスクリーニング（Phase 9C・2段階）
- スクリーニング実施数: **0**
- SES企業と判定: **0**
- インセンティブ言及: **0**
- 粗利%明示: **0**
- 粗利58%以上: **0**

## スクリーニング方式
- 第1段階: `"{会社名}" SES` でSES企業判定
- 第2段階: SES判定=yes のみ `"{会社名}" "営業" "粗利"` 等でインセンティブ検索

## 出力ファイル
- `phase9a_gbiz_companies.csv`
- `phase9b_nta_companies.csv`
- `phase9_new_companies.csv`
- `phase9_screening_results.csv`
- `phase9_summary.md`

## APIトークン状況
gBizINFO / 国税庁API のトークン設定手順は `phase9_api_application_guide.md` を参照。

