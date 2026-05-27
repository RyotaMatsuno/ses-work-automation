# TASKS.md - mail_pipeline コスト最適化改修

## タスクリスト（Codexはこの順番で実装する）

- [ ] TASK1: analyze_final.py からのパターンインポート確認
  - `from analyze_final import SKIP_PATTERNS, ENGINEER_PATTERNS, PROJECT_PATTERNS, classify_by_rule` が動くか確認
  - 動かない場合はパターン定数をmail_pipeline.py内にコピーして定義

- [ ] TASK2: classify_email_v2() 関数を mail_pipeline.py に追加
  - 引数: emails (list of dict with keys: subject, sender, body, index)
  - 処理:
    1. classify_by_rule(subject, sender) でルール分類
    2. skip → results[index] = {"type": "other"} （スキップ扱い）
    3. project確定 → Batch APIの extract_project リクエスト追加
    4. engineer確定 → Batch APIの extract_engineer リクエスト追加
    5. unknown → Batch APIの classify リクエスト追加
    6. Batch API に一括送信（requests で直接 POST）
    7. status=ended になるまでポーリング（30秒おき、最大120分）
    8. 結果を results[index] に格納して返す
  - フォールバック: Batch API例外時は classify_email() を個別呼び出し

- [ ] TASK3: main() 処理ループを改修
  - classify_email(subject, body) の呼び出し箇所を classify_email_v2 の結果参照に変更
  - filter_engineers_by_skills の top_n を MATCH_TOP_N から 3 に変更
  - body[:8000] を body[:200] に変更（抽出プロンプト用）

- [ ] TASK4: 構文チェック
  - python -m py_compile mail_pipeline.py

- [ ] TASK5: DRY_RUN テスト（IMAP接続なし）
  - 既存の DRY_RUN 機能がある場合はそれを使う
  - ない場合はインポートチェックのみ: `python -c "from mail_pipeline.mail_pipeline import classify_email_v2; print('OK')"`

## 注意事項
- CLAUDE_opt.md の禁止事項を必ず守ること
- 既存関数は一切削除・変更しない
- 追加するのは classify_email_v2() のみ
- main() の変更は最小限（3箇所だけ）
