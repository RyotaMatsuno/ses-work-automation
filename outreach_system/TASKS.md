# TASKS.md — アポ取りシステム 実装チェックリスト

最終更新: 2026-05-25

## Phase A: データ基盤

- [x] 1. `targets.csv` サンプルファイルを作成（3行のサンプルデータ入り）
- [x] 2. `history.json` 初期ファイルを作成（空のdict: {}）
- [x] 3. `outreach.py` 作成: targets.csvを読み込んで一覧をprintするだけ
- [x] 4. 除外判定実装: memoに「断り」含む行をスキップして除外数をprint

## Phase B: 再送制御

- [x] 5. history.jsonの読み書き関数実装
- [x] 6. 再送チェック実装: 前回送信から180日未満はskip
- [x] 7. dry_run時にどの送信先が対象かをprint確認

## Phase C: メール送信

- [x] 8. `send_mail.py` 作成: SMTP SSL送信関数（dry_run引数対応）
- [x] 9. テンプレートA/B切り替えロジック実装（typeフィールドで判定）
- [x] 10. CC: r-matsuno@terra-ltd.co.jpを自動付与

## Phase D: 統合・出力

- [x] 11. `outreach.py` にPhase A〜Cを統合
- [x] 12. `result_outreach.json` 出力実装
- [x] 13. `--dry-run` / `--run` 引数対応
- [x] 14. `python outreach.py --dry-run` でエンドツーエンド動作確認（送信なし）

## 完了済み
（なし）
