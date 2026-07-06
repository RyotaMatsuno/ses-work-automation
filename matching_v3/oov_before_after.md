# OOV Before/After Report (2026-07-03)

## データソース
- 案件: structured.jsonl（直近30日 case_id フィルタ） 1345 件
- 人材: poc_engineers.json 154 名
- スキルトークン数（技術スキル分母）: 6316

## OOV率
| 指標 | Before | After | 差分 |
|------|--------|-------|------|
| OOV率 | 50.9% | 28.2% | -22.7pt |
| OOV件数 | 3216 | 1773 | -1443 |
| 対象件数 | 6316 | 6285 | — |

## マッチ候補数（skill_gate通過案件数）
- Before: 1007
- After: 1175
- 増分: +168

## 目標
- 目標 OOV率: 25%以下（起点 41%）
- 達成: No (28.2%)

## 変更内容
- skill_pre_normalize.py: NFKC/カタカナ/記号/運用保守サフィックス正規化
- skill_aliases.json: OOV上位語のエイリアス追加
- matcher/skill_gate: 辞書参照前に pre_normalize 適用
