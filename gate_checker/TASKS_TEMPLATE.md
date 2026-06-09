# TASKS テンプレート（gate_checker対応版）

## フェーズ完了時のgate_checker呼び出し

各フェーズ完了後に以下を実行。exit 1 の場合は修正後に再実行。exit 2 はスキップ（続行可）。

```bash
# 要件定義完了後
python gate_checker/gate_check.py --phase requirements --file SPEC.md --tasks-file TASKS.md
# → exit 0: 次へ / exit 1: SPEC.md修正 / exit 2: スキップして次へ

# 設計完了後
python gate_checker/gate_check.py --phase design --file TASKS.md --tasks-file TASKS.md
# → exit 0: 次へ / exit 1: TASKS.md修正 / exit 2: スキップして次へ

# 実装完了後
python gate_checker/gate_check.py --phase implementation --dir src/ --tasks-file TASKS.md
# → exit 0: 次へ / exit 1: コード修正 / exit 2: スキップして次へ

# テスト完了後
python gate_checker/gate_check.py --phase test --file test_results.json --tasks-file TASKS.md
# → exit 0: デプロイGO / exit 1: テスト追加 / exit 2: スキップしてデプロイGO
```
