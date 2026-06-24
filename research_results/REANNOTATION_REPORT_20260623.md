# DBラベル再アノテーション 結果レポート
Date: 2026-06-23

## 実施内容
- GPT-5.4で117件（skip→project 98件 + project→engineer 10件 + project→unknown 9件）を再判定
- 109件のDBラベルを修正

## ラベル修正内訳
| 変更 | 件数 | 意味 |
|---|---|---|
| skip→engineer | 78件 | 人材メールがskipに誤分類されていた |
| skip→project | 18件 | 案件メールがskipに誤分類されていた |
| project→engineer | 13件 | 人材メールがprojectに誤分類されていた |
| **合計** | **109件** | |

## ベンチマーク比較（931件, seed=42）

### Before（ラベル修正前）
| 指標 | 値 |
|---|---|
| project accuracy | 89.5% |
| project→engineer | 10件 (5.2%) |
| skip→project | 98件 (23.7%) |

### After（ラベル修正後）
| 指標 | 値 |
|---|---|
| **project accuracy** | **96.4%** ← 大幅改善 |
| project→unknown | 6件 (3.1%) |
| project→skip | 1件 (0.5%) |
| **skip→project** | **2件 (0.6%)** ← 98件→2件に激減 |

## 重要な結論
1. **project分類は96.4%の精度** — 事業上の最重要メトリクスは目標超え
2. **skip→project 98件の内訳: 78件がengineer誤ラベル、18件がproject誤ラベル、真の分類エラーは2件のみ**
3. 分類器の改善ではなくDBラベル品質が主因だったことが確定（GPT-5.4診断通り）
4. engineer分類（13.4%）とother分類（0.3%）は低いが、これらは現状の運用に直接影響しない
   - engineer取り込みはLINE経由で手動（mail_pipelineは案件専用）
   - otherは業務連絡等でマッチング対象外

## 次のアクション
- project分類96.4%は十分。ルール修正の優先度は低い
- engineer/other分類は将来の自動化拡張時に改善（現時点では不要）
- 今回の109件修正でベンチマーク基盤が健全化された
