# TASKS テンプレート（gate_checker 6フェーズ対応版）

## フェーズ完了時のgate_checker呼び出し

各フェーズ完了後に以下を実行。exit 1 の場合は修正後に再実行。exit 2 はスキップ（続行可）。

```bash
# 調査完了後
python gate_checker/gate_check.py --phase research --file research_memo.txt --tasks-file TASKS.md
# → exit 0: 次へ / exit 1: 調査修正 or 壁打ち / exit 2: スキップして次へ

# 要件定義完了後
python gate_checker/gate_check.py --phase requirements --file SPEC.md --tasks-file TASKS.md
# → exit 0: 次へ（松野確認LINE送信） / exit 1: SPEC.md修正 / exit 2: スキップして次へ

# 設計完了後
python gate_checker/gate_check.py --phase design --file TASKS.md --tasks-file TASKS.md
# → exit 0: 次へ（松野確認LINE送信） / exit 1: TASKS.md修正 / exit 2: スキップして次へ

# 実装前確認
python gate_checker/gate_check.py --phase pre_impl --file TASKS.md --tasks-file TASKS.md
# → exit 0: 実装開始可 / exit 1: TASKS.md修正 or 壁打ち / exit 2: スキップして次へ

# 実装完了後
python gate_checker/gate_check.py --phase implementation --file src/main.py --tasks-file TASKS.md
python gate_checker/gate_check.py --phase implementation --dir src/ --tasks-file TASKS.md
# → exit 0: 次へ / exit 1: コード修正 or 壁打ち / exit 2: スキップして次へ

# テスト完了後
python gate_checker/gate_check.py --phase test --file test_results.json --tasks-file TASKS.md
# → exit 0: デプロイGO（松野確認LINE送信） / exit 1: テスト追加 / exit 2: スキップしてデプロイGO
```

## 松野確認フロー

- requirements / design / test フェーズは GPT判定に関わらず松野確認推奨
- 松野確認トリガー時はLINEに通知される
- OK確認後は LINE に `gate {phase} ok` と送信
