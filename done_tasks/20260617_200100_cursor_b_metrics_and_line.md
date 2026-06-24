# Cursor作業指示 b: mail_pipeline メトリクス記録ロジック + 進捗LINE通知拡張

最終更新: 2026-06-17 20:00 (ジョブズ作成)
GPT-5.4 round1/round2 壁打ち合意済み

## 背景

2026-06-13〜17 の案件登録停止事案で、SES_MailPipeline タスクが 6/15 19:00 以降無効化されていたことに
気づくのに 2 日以上かかった。原因は「動作メトリクスを記録・通知する仕組みがなかった」ため。

GPT-5.4 round2 でも「matching_v2 課金停止の証拠」「4連続実行の証拠」「backlog/処理時間」を
記録・可視化することが推奨されている。

## 対象ファイル

- 修正対象: `mail_pipeline/mail_pipeline.py`
- 新規作成: `mail_pipeline/metrics_recorder.py`
- 新規作成: `mail_pipeline/metrics.jsonl` (実行ごとの追記、ローテーション付き)
- LINE 通知関数: `line_webhook/notify.py` (既存) を流用

## 作業内容

### Phase 1: メトリクス定義
1回の mail_pipeline 実行で以下を記録:

| フィールド | 型 | 説明 |
|---|---|---|
| ts_start | datetime ISO | 開始時刻(UTC) |
| ts_end | datetime ISO | 終了時刻(UTC) |
| elapsed_seconds | float | 実行所要時間 |
| accounts_fetched | int | IMAP接続成功アカウント数 |
| mails_fetched | int | 取得メール総数 |
| mails_new | int | 重複除外後の新規メール数 |
| mails_skipped_dup | int | 重複でskipされた数 |
| batch_api_calls | int | Batch API送信回数 |
| batch_api_items_total | int | Batch API投入アイテム総数 |
| notion_engineer_created | int | engineer DB 新規作成数 |
| notion_project_created | int | project DB 新規作成数 |
| notion_errors | int | Notion API エラー回数 |
| imap_errors | int | IMAP接続/取得エラー回数 |
| cost_usd | float | この実行の累積コスト(Claude haiku Batch分) |
| process_limit | int | この実行の PROCESS_LIMIT |
| fetch_limit | int | この実行の FETCH_LIMIT |
| exit_code | int | 0=成功, 1=失敗 |
| error_message | str | exit_code!=0 時の最初のエラー |

### Phase 2: metrics_recorder.py 実装
```python
# -*- coding: utf-8 -*-
"""mail_pipeline 実行メトリクスを metrics.jsonl に追記する."""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
METRICS_PATH = BASE / "metrics.jsonl"
MAX_SIZE_MB = 50  # 50MB超でローテーション

class MetricsRecorder:
    def __init__(self):
        self.start = time.time()
        self.metrics = {
            "ts_start": datetime.now(timezone.utc).isoformat(),
            "accounts_fetched": 0,
            "mails_fetched": 0,
            "mails_new": 0,
            "mails_skipped_dup": 0,
            "batch_api_calls": 0,
            "batch_api_items_total": 0,
            "notion_engineer_created": 0,
            "notion_project_created": 0,
            "notion_errors": 0,
            "imap_errors": 0,
            "cost_usd": 0.0,
            "process_limit": 0,
            "fetch_limit": 0,
            "exit_code": 0,
            "error_message": "",
        }
    
    def inc(self, key, n=1):
        self.metrics[key] = self.metrics.get(key, 0) + n
    
    def set(self, key, value):
        self.metrics[key] = value
    
    def finalize(self, exit_code=0, error_message=""):
        self.metrics["ts_end"] = datetime.now(timezone.utc).isoformat()
        self.metrics["elapsed_seconds"] = round(time.time() - self.start, 2)
        self.metrics["exit_code"] = exit_code
        self.metrics["error_message"] = error_message[:500] if error_message else ""
        self._rotate_if_needed()
        with open(METRICS_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(self.metrics, ensure_ascii=False) + "\n")
        return self.metrics
    
    def _rotate_if_needed(self):
        if not METRICS_PATH.exists():
            return
        if METRICS_PATH.stat().st_size > MAX_SIZE_MB * 1024 * 1024:
            archive = METRICS_PATH.with_suffix(f".jsonl.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak")
            METRICS_PATH.rename(archive)
```

### Phase 3: mail_pipeline.py 統合
- import: `from mail_pipeline.metrics_recorder import MetricsRecorder`
- main() 冒頭: `metrics = MetricsRecorder()`
- 取得/送信ループ内で `metrics.inc("mails_fetched", 1)` 等
- main() 終端: `metrics.finalize(exit_code=0)`
- 例外時: `metrics.finalize(exit_code=1, error_message=str(e))`

### Phase 4: LINE通知拡張
- 毎時実行後、summary を松野公式LINEに push
- ただし `push_or_log()` を使用(LINE月200通上限に注意、引き継ぎプロトコル p22 参照)
- フォーマット例:
```
[mail_pipeline 20:00台]
取得:48 新規:137 skip:11
送信:Batch 13件 / Notion登録:0/0
所要:78秒 cost:$0.012
✅正常 (matching_v2 skipped)
```

- 異常時(exit_code != 0 または notion_errors > 0)は **必ず即時push**

### Phase 5: 日次サマリー
夜間に `metrics.jsonl` を集計して日次サマリーをLINE通知:
- 23:00 cron で起動
- 当日の全実行メトリクスを集計
- 案件登録数推移、コスト推移、エラー件数
- 引き継ぎプロトコル p22 のLINE月200通上限を考慮(夜1回のみ)

`metrics_daily_summary.py` として別ファイルで実装。

## 完了条件

- metrics_recorder.py 実装、ユニットテスト4件以上
- mail_pipeline.py に統合、毎時 metrics.jsonl 追記確認
- LINE通知が松野チャンネルに届く(毎時 + 異常時即時 + 23:00日次)
- ローテーション動作確認(50MB)
- LINE月200通上限に収まる設計(push数試算をPRに含める)

## ゲート

- ゲート①: SPEC設計後 `python gate_checker/gate_check.py --phase design --file mail_pipeline/SPEC_metrics.md`
- ゲート②: 実装完了後 `python gate_checker/gate_check.py --phase implementation --file mail_pipeline/metrics_recorder.py`

## 参照

- 引き継ぎ: 2026-06-17_メール基盤緊急復旧 (■未完了 #2)
- ジョブズ行動憲法 #22 (LINE上限考慮)
- GPT-5.4 round2 (P3引き継ぎメモ整備の要件)
