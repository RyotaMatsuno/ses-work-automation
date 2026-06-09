# gate_checker

全開発フェーズ（要件定義・設計・実装・テスト）でGPT-4oによる自動レビューを行う。

## exit codes

| code | 意味 | Cursorの対応 |
|------|------|--------------|
| 0 | GO（問題なし） | 次フェーズに進む |
| 1 | NG（問題あり） | 修正してから再実行 |
| 2 | スキップ（日次上限超過） | 次フェーズに進む（ブロック不要） |

## 重要: exit 1 と exit 2 の違い

- **exit 1** = コードや設計に問題がある → 必ず修正してから進む
- **exit 2** = 今日のAPI呼び出し上限に達した → そのまま続行してよい

## 呼び出し例

```bash
python gate_checker/gate_check.py --phase requirements --file SPEC.md --tasks-file TASKS.md
python gate_checker/gate_check.py --phase design     --file TASKS.md --tasks-file TASKS.md
python gate_checker/gate_check.py --phase implementation --dir src/  --tasks-file TASKS.md
python gate_checker/gate_check.py --phase test       --file test_results.json --tasks-file TASKS.md
```
