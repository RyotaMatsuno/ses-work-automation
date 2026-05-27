# SPEC.md - マッチングロジック改善

## 修正1: run_reverse_matching に全件渡すための分割バッチ処理
### ファイル: line_webhook/webhook_server.py
### 対象: run_reverse_matching の呼び出し箇所

現状: projects[:20] に制限しているため70件中20件しか見ていない
修正: 30件ずつバッチで分割してClaude APIを複数回呼び、結果をマージする

```python
def run_reverse_matching_full(engineer, projects):
    """全案件を30件バッチで処理してマッチング結果をマージ"""
    BATCH_SIZE = 30
    all_matches = []
    for i in range(0, len(projects), BATCH_SIZE):
        batch = projects[i:i+BATCH_SIZE]
        result = run_reverse_matching(engineer, batch)
        all_matches.extend(result.get("matches", []))
    # スコア降順でソートして重複除去（project_nameで）
    seen = set()
    unique = []
    for m in sorted(all_matches, key=lambda x: x.get("score", 0), reverse=True):
        name = m.get("project_name", "")
        if name not in seen:
            seen.add(name)
            unique.append(m)
    return {"matches": unique}
```

既存の `run_reverse_matching(engineer, active_projects)` の呼び出しを
`run_reverse_matching_full(engineer, active_projects)` に変更する（全箇所）。

---

## 修正2: 上振れ15万超の案件を除外
### ファイル: line_webhook/matching_logic.py
### 対象: categorize_match() 関数

現状: 上振れ候補（upfuri_candidate）は必須全○+尚可1つ以上○のケースで案件単価+2万提案している
修正: engineer_price との乖離が15万超の案件はNGカテゴリに分類する

```python
# categorize_match 関数内の先頭に追加
# 上振れ上限チェック: エンジニア単価より15万以上高い案件は基本無理
if ep > 0 and pp > 0 and (pp - ep) > 15:
    return {"category": "ng", "gross": gross, "reason": f"上振れ{pp-ep}万超（上限15万）"}
```
