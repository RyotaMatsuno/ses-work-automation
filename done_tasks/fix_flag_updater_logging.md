【Cursor作業指示】
対象ファイル: ses_work/flag_auto_updater/run_flag_updater.py
作業内容: _setup_logging() の force=True によるログ乗っ取り修正

---

## 完了メモ（2026-06-19）

- `run_flag_updater._setup_logging()`: ルートロガーに既存ハンドラーがある場合は `flag_updater` 用 FileHandler のみ追加（`force=True` 廃止）
- 単独起動時は従来通り `basicConfig`（File + Stream）
- `flag_auto_updater/tests/test_setup_logging.py` 3件追加・全パス
- `matching_v3.py` コメント修正
