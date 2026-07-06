# 単価再抽出 dry-run 20260625

対象: ステータス=募集中 AND 単価=null AND 案件情報原文≠空

## サマリー

| 項目 | 件数 |
|------|------|
| 対象 | 75 |
| 抽出成功 | 12 |
| スキップ | 63 |

## 次のアクション

python matching_v3/recover_prices.py --execute で12件をNotionに書き込み。
高品質率 78.2% → 約81% 見込み。
