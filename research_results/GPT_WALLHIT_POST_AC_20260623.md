# GPT-5.4壁打ち: Task AC完了後の3課題分析
Date: 2026-06-23

## 931件ベンチマーク結果（Task AC完了後）
- project→engineer: 10件 (5.2%) ← 前回32件から大幅改善
- project→unknown: 9件
- skip→project: 98件 (23.7%) ← DBラベル品質問題が主因
- project accuracy: 89.5%

## GPT-5.4判断
### 課題1: 分類精度（P1）
- 診断: skip→project 98件はDBラベル品質問題の露出が主因
- 対策: DBラベル再アノテーション → skip 98件全件レビュー → ルール修正は後
- project→engineer 5.2%は条件付き許容（再アノテーション後に再評価）

### 課題2: daily_statsカウンタバグ（P0）
- processed_casesにmatched記録あるのにdaily_stats match_count=0
- 対策: processed_casesを正とする集計クエリ化 + daily_statsをバッチ再計算に

### 課題3: nightly_jobzキュー汚染（P1）
- push_fail 20件: 削除OK
- 法人化TODO 7件: 恒久バックログへ移管（キューから除去）
- 根本対策: push_failがキューに入る原因を特定して投入拒否ルール追加

## 優先順: daily_stats > キュー掃除 > 分類精度
