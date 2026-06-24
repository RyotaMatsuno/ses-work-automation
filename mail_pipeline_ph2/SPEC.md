# SPEC.md — mail_pipeline フェーズ2

最終更新: 2026-06-10

## B. バリデーション

### B-04 必須項目と登録方針

| 条件 | 動作 |
|---|---|
| 氏名欠損 | 登録スキップ（SKIP） |
| スキル欠損 | REVIEW登録（Notionに登録・提案対象フラグ=False・備考追記） |
| 稼働開始日欠損 | REVIEW登録（Notionに登録・提案対象フラグ=False・備考追記） |
| 外国籍関連キーワード | REVIEW登録・提案対象フラグ=False |
| 関東圏外（例外条件なし） | REVIEW登録・提案対象フラグ=False |
| 単価要確認 | REVIEW登録・提案対象フラグ=False |

優先順: SKIP > REVIEW > OK

## C. 鮮度判定

- `matching_v3/staleness_checker.check()` を正とする
- Notion API クエリでは `情報取得日` でフィルタしない
- `提案対象フラグ=True` のみ取得し、Python 側で鮮度判定
