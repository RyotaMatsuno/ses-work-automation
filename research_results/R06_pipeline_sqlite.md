# R06: mail_pipeline SQLite基盤調査
調査日: 2026-06-18

## 結論（1行）
`raw_inbox.py` の UNIQUE 制約と移行ロジックは基本機能として成立しているが、**WAL / busy_timeout 未設定・プロセス間排他なし・insert の SELECT→INSERT 競合** により、30分スケジューラと手動実行の衝突時に `database is locked` や二重 LLM 処理のリスクが残る（年6000件規模の性能問題は当面なし）。

## テーブル定義分析

### raw_emails（`raw_inbox.py:18-33`）

| カラム | 型 | 制約 | 備考 |
|---|---|---|---|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | — |
| message_id | TEXT | **UNIQUE** | NOT NULL **なし**（空文字は `insert_raw_email` 側で早期 return） |
| account, received_at, sender, subject, body_text, body_hash, attachment_names, classify_result | TEXT | 制約なし | NULL 許容 |
| has_attachment | INTEGER | DEFAULT 0 | — |
| processed | INTEGER | DEFAULT 0 | 0=未処理, 1=処理済み |
| created_at | TEXT | DEFAULT datetime('now') | — |

**インデックス**
- `message_id UNIQUE` により SQLite が自動的にユニークインデックスを生成（明示 `CREATE INDEX` なし）
- `processed` / `received_at` への追加インデックスなし（現行件数では問題にならないが、`load_processed_ids()` の `WHERE processed = 1` 全件読み込みは件数比例）

**monthly_stats（VIEW, `raw_inbox.py:35-41`）**
- `strftime('%Y-%m', received_at)` × `classify_result` で GROUP BY
- `received_at` が NULL/空の行は `month = NULL` バケットに集約される

**WAL / PRAGMA 設定**
- `get_connection()`（`raw_inbox.py:49-53`）は `sqlite3.connect(path)` のみ。**journal_mode=WAL・busy_timeout・foreign_keys 等の PRAGMA 設定なし**
- デフォルト journal_mode は **DELETE**（Python sqlite3 / SQLite 標準）
- Python 3.12 の `sqlite3.connect` デフォルト `timeout=5.0` 秒がロック待ちに適用されるが、`raw_inbox.py` では明示していない

**本番 DB 状態（ファイルシステムのみ確認、`raw_inbox.db` は未オープン）**
- `processed_ids.json` は存在せず、`processed_ids.json.bak`（約 82KB）のみ → 移行完了済みと推定

## 移行ロジック分析

### 呼び出し経路（`mail_pipeline.py:336-346`）

```python
def ensure_raw_inbox_ready() -> None:
    init_raw_inbox_db(RAW_INBOX_DB)
    if PROCESSED_IDS_PATH.exists():  # processed_ids.json の存在のみ判定
        try:
            migrated = migrate_processed_ids_json(...)
        except Exception as e:
            log(f"processed_ids移行エラー: {e}")  # 失敗してもパイプラインは継続
```

### migrate_processed_ids_json（`raw_inbox.py:217-267`）の挙動

| 観点 | 実装 | 評価 |
|---|---|---|
| 移行トリガー | `processed_ids.json` が存在するときのみ | `.bak` 存在はスキップ条件に**含まれない**（json が無ければ何もしない） |
| DB 書き込み | 全 ID をループ後 **1 回 `commit()`** | クラッシュ時: commit 前なら DB 変更なし・json 温存 → **再実行可能** |
| 既存行 | `processed=0` なら UPDATE、`processed=1` ならスキップ | 冪等 |
| 新規行 | `INSERT (message_id, processed=1, classify_result='migrated')` のみ（本文なし） | 移行専用の「ゴースト行」が生成される |
| .bak リネーム | **`commit()` 成功後**に `bak.unlink()` → `shutil.move(json→bak)` | 順序は妥当（DB 確定後にソース退避） |
| 例外時 | `finally: conn.close()` のみ。**rollback 明示なし**（未 commit なら自動破棄） | 許容範囲 |
| commit 後・move 前クラッシュ | json 残存 → 次回再移行（冪等） | 復旧可能 |
| move 成功後 | json 消滅・bak 残存 | 本番はこの状態（bak のみ存在） |

**部分移行からの復旧手段**
1. **自動**: json が残っていれば次回 `ensure_raw_inbox_ready()` で再実行（UPDATE/INSERT は冪等）
2. **手動**: json が消えたが DB に不足がある場合 → `processed_ids.json.bak` から json を復元して再実行可能
3. **移行失敗が続く場合**: 例外はログのみでパイプライン継続。`load_processed_ids()` は DB の `processed=1` のみ参照するため、**移行未完了＋json 残存時は古い json の ID が DB に反映されず、同一メールの再 LLM 処理が発生しうる**

**テストカバレッジ**
- `tests/test_raw_inbox.py::test_migrate_processed_ids_json`: 1535 件移行・json 削除・bak 生成を検証
- クラッシュ中間状態・並行移行のテストなし

## 同時実行安全性

### 実行モデル
- `SPEC.md` / `TASKS.md`: Windows タスクスケジューラで **30分おき** `run_pipeline.bat` 実行
- `run_pipeline.bat`: **排他ロック・PID ファイル・mutex なし**。手動 `python mail_pipeline.py` と衝突可能
- 1 プロセス内はシングルスレッドだが、**複数プロセスが同一 `raw_inbox.db` を同時オープン**しうる

### INSERT 時の重複処理

| 関数 | 方式 | 同時実行時 |
|---|---|---|
| `insert_raw_email` | SELECT → INSERT or UPDATE（`raw_inbox.py:98-150`） | **TOCTOU 競合**: 2 プロセスが同時に SELECT 空→両方 INSERT → 片方が `IntegrityError`（未 catch → `_save_all_emails_to_raw_inbox` で log のみ） |
| `mark_processed` | `INSERT ... ON CONFLICT DO UPDATE`（`raw_inbox.py:179-186`） | **アトミック** ✓ |
| `update_classify_result` | 同上 ON CONFLICT | **アトミック** ✓ |

**processed フラグのライフサイクル**
- 初期値: `DEFAULT 0`（新規 INSERT 時）
- 更新: `save_processed_id()` → `mark_processed()`（各メール処理完了時、`mail_pipeline.py:328-333, 1612+`）
- 起動時: `load_processed_ids()` で **全 `processed=1` をメモリ set にロード**（`raw_inbox.py:157-166`）
- **問題**: 2 プロセスが同時起動すると、両方が同じ未処理 ID を「新規」と判定し、**LLM 二重実行・Notion 二重登録の可能性**（SQLite だけでは防げない）

### ロック関連

| 設定 | 現状 | 影響 |
|---|---|---|
| journal_mode | DELETE（デフォルト） | 書込中は読取もブロックされやすい |
| WAL | **未設定** | 読み書き並行性能が劣る |
| busy_timeout | Python デフォルト 5 秒（暗黙） | 長時間 LLM 処理中に別プロセスが DB 書込 → 5 秒待ち後 `OperationalError: database is locked` |
| 接続寿命 | 操作ごとに open → commit → close | 長時間トランザクションは無い（ロック保持時間は短い） |

**衝突シナリオ（30分スケジューラ × 手動実行）**
1. プロセス A が LLM 処理中（DB は都度 close）
2. プロセス B が起動 → `load_processed_ids` / `insert_raw_email` / `mark_processed` で DB アクセス
3. タイミング次第で **(a) locked エラーで raw_inbox 保存失敗**（log のみ、メール取りこぼしリスク）または **(b) 同一 msg_id の二重 LLM 処理**

`pipeline.log` 内に `database is locked` / `raw_inbox` 関連ログは未検出（2026-06-18 時点）だが、コード上の構造リスクは残存。

## 将来スケーラビリティ

**想定データ量**: 月 500 件 × 12 ヶ月 = **年 6,000 件以上**（調査指示どおり）

| 観点 | 見通し |
|---|---|
| 行数 6,000〜数万 | SQLite は問題なし（単一テーブル百万行規模まで実用） |
| 行サイズ | `body_text` 全文保存 → 1 行 5〜50KB 想定、年間 **数十〜300MB** 程度 |
| クエリ性能 | `message_id` UNIQUE 索引で point lookup は O(log n)。`load_processed_ids` の全件 scan は 6,000 件で数 ms〜数十 ms |
| monthly_stats VIEW | 6,000 行 GROUP BY は瞬時。10 万行超で初めて体感 |
| VACUUM | 通常 INSERT のみなら **不要**。大量 DELETE アーカイブ時のみ検討 |
| init_db 毎操作 | 各関数が `init_db()` 呼び出し → `CREATE IF NOT EXISTS` のメタデータ読取が毎回発生（微オーバーヘッド、6,000 件規模では許容） |
| ボトルネック移行点 | **件数よりプロセス並行と WAL 未設定**が先に問題化。10 万行・数百 MB 超でバックアップ時間・`load_processed_ids` メモリ（全 ID set）を再評価 |

## 推奨アクション

- [ ] **P0**: `get_connection()` に `PRAGMA journal_mode=WAL` と `timeout=30.0`（秒）を明示設定し、同時アクセス時の `database is locked` を低減
- [ ] **P0**: `run_pipeline.bat` または `mail_pipeline.py` 先頭に **単一実行ロック**（Windows `msvcrt` / lock ファイル / `portalocker` 等）を追加し、スケジューラと手動実行の二重起動を防止
- [ ] **P0**: `insert_raw_email` を `INSERT ... ON CONFLICT(message_id) DO UPDATE` に統一し、SELECT→INSERT の TOCTOU と IntegrityError を排除
- [ ] **P1**: `migrate_processed_ids_json` を **1 トランザクション + commit 成功後のみ move** のまま、失敗時は `ensure_raw_inbox_ready` で **移行未完を ERROR 終了**（または processed 件数と json 件数の照合）に変更し、サイレント継続をやめる
- [ ] **P1**: `CREATE INDEX IF NOT EXISTS idx_raw_emails_processed ON raw_emails(processed)` を追加（`load_processed_ids` 用。6,000 件では効果小だが低コスト）
- [ ] **P1**: `message_id TEXT NOT NULL` をスキーマに追加（新規 DB は ALTER、既存はマイグレーションスクリプト）し、ゴースト行のデータ品質を向上
- [ ] **P2**: 年次アーカイブ方針（例: 12 ヶ月超の `body_text` を別テーブル/ファイルへ退避）を Phase 3 以降の設計に明記
- [ ] **P2**: 移行中間クラッシュ・二重 `migrate_processed_ids_json` 呼び出しの pytest を追加
