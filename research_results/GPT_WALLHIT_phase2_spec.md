# GPT-5.4壁打ち: Phase 2 SPEC設計
日時: 2026-06-26

## GPT合意事項

### 順序変更（GPT推奨）
- 2A0: 171→0 retrieval collapse診断（P0）
- 2A1: ステータス管理 + Active Pool定義
- 2A2: スキル正規化
- 2B: ベンチマーク設計 + annotation setup
- 2C: retrieval sanity回復後に初回ベンチマーク実行

### 主要な指摘
1. 171→0はランキング問題ではなく候補生成の構造的欠陥。P0優先。
2. 50件ベンチマークはパイロットとして十分、統計的検証には不足。Phase 3で150-300件に拡大。
3. アノテーション方式: pooled annotation推奨（top-N only は recall測定不可、全208は非効率）
   - 現システムのtop-10
   - フィルター緩和版のtop-10
   - セマンティック検索のtop-10
   - Active poolからランダム10
   → 案件あたり20-35名をアノテーション
4. ラベル定義: binary match/no-matchではなく3段階（Strong match / Interview-worthy / Not a match）
5. メトリクス: Recall@10単体ではなくスイート（zero-result rate, >=10候補率, Recall@10, strong-match@10, active-pool調整版）
6. 失敗分類学: skill synonym miss / over-strict AND / missing status / missing data / rank issue / no-supply

### Goodhart's Lawリスク（GPT指摘6件）
1. ラベル基準の緩和によるRecall水増し
2. 簡単なケースだけベンチマークに入れる
3. ジェネラリストを上位に詰め込む
4. ベンチマークケースにオーバーフィット
5. Active Pool狭義定義で分母を縮小
6. プロファイルキーワードスタッフィング
7. フィルター緩和過剰で全員返す

### ガードレール
- strict "strong match" と broader "interview-worthy" の2指標を常に併記
- stratifiedベンチマーク（common/rare skills, exact/fuzzy, seniority, domain）
- precision/強match率を常にrecallと併記
- held-out setをPhase 3で維持
