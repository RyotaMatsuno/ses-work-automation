# SPEC.md - スクリプト別コストトラッカー

## 概要
Jobzが使うAnthropicモデルのコストを、スクリプト（呼び出し元）別に記録してNotionに集計するシステム。

## 対象スクリプト（コスト発生源）
| スクリプト名 | ソースファイル | 用途 |
|---|---|---|
| mail_pipeline | ses_work/mail_pipeline.py | メール受信→Notion登録 |
| matching_v2 | ses_work/matching_v2/matching_v2.py | AIマッチングエンジン |
| notify_line | ses_work/matching_v2/notify_line.py | LINE通知 |

## 実装方針

### Step 1: cost_logger.py（各スクリプトから呼ぶロギング関数）
**インターフェース**
```python
from usage_tracker.cost_logger import log_cost

log_cost(
    script_name="matching_v2",
    model="claude-haiku-4-5-20251001",
    input_tokens=1200,
    output_tokens=300,
    cached_tokens=800,  # 省略可、デフォルト0
)
```

**ログ保存先**: `ses_work/usage_tracker/cost_log.jsonl`
**フォーマット（1行1レコード）**:
```json
{"ts": "2026-05-26T09:00:00", "script": "matching_v2", "model": "claude-haiku-4-5-20251001", "input_tokens": 1200, "output_tokens": 300, "cached_tokens": 800, "cost_usd": 0.00042}
```

### Step 2: cost_calculator.py（トークン→USD→円）
モデル別単価（2026年5月時点）:

| モデル | input ($/1M) | output ($/1M) | cache_read ($/1M) |
|---|---|---|---|
| claude-haiku-4-5-20251001 | 0.80 | 4.00 | 0.08 |
| claude-sonnet-4-6 | 3.00 | 15.00 | 0.30 |
| claude-opus-4-6 | 15.00 | 75.00 | 1.50 |

為替: 1USD = 155円（固定。.envで上書き可能 `USD_JPY_RATE`）
未知モデルはsonnet単価にフォールバックしてwarning出力。

### Step 3: notion_writer.py（Notion DB作成・書き込み）
**親ページ**: SESナレッジWikiページ ID = `353450ff-37c0-8145-9e3e-d80c8c8ed594`
**DB名**: `コスト管理DB`

DB作成は初回のみ。既存DBが存在する場合はスキップ（DB IDを `usage_tracker/notion_db_id.txt` に保存して再利用）。

**DBプロパティ**:
| プロパティ名 | タイプ |
|---|---|
| 日付 | date |
| スクリプト | select |
| モデル | select |
| 入力トークン | number |
| 出力トークン | number |
| コスト(USD) | number |
| コスト(円) | number |
| 月次累計(円) | number |

### Step 4: usage_tracker.py（日次集計メイン）
処理フロー:
1. `cost_log.jsonl` を読み込み
2. 前日分（昨日の日付）をフィルタ
3. スクリプト別・モデル別に集計
4. 当月累計を計算（アーカイブ + 当日ログから）
5. Notionに書き込み
6. 処理済みレコードを `cost_log_archive_YYYYMM.jsonl` に移動
7. `cost_log.jsonl` から処理済み分を削除

### Step 5: run_usage_tracker.bat
```bat
@echo off
cd /d C:\Users\ma_py\OneDrive\デスクトップ\ses_work
python usage_tracker/usage_tracker.py >> usage_tracker/usage_tracker.log 2>&1
```

### Step 6: setup_scheduler.py
Windowsタスクスケジューラに「usage_tracker_daily」を毎日09:05に登録。
`schtasks /create` コマンドを使用。既存タスクがある場合は `/f` で上書き。

## ファイル構成
```
ses_work/
  usage_tracker/
    __init__.py
    cost_logger.py
    cost_calculator.py
    usage_tracker.py
    notion_writer.py
    setup_scheduler.py
    run_usage_tracker.bat
    cost_log.jsonl        # 自動生成
    usage_tracker.log     # 自動生成
    notion_db_id.txt      # 自動生成（初回DB作成後）
```

## 既存スクリプトへの変更範囲
- `matching_v2/matching_v2.py`: Claude API呼び出し後に `log_cost()` を追加
- `mail_pipeline.py`: 同上
- `matching_v2/notify_line.py`: Claude呼び出しがある場合のみ追加
- **変更は最小限。既存ロジックには一切触らない**
