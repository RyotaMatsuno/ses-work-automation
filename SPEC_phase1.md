# Phase 1 SPEC: Global Kill-Switch Overhaul

## 目的
コスト爆発を止める唯一のセーフガードが主犯（SES_MatchingV3等）を対象外にしている。
5分以内に実効性のあるグローバルキルスイッチに改修する。

## 1. 定数の変更

```python
# 変更前
HOURLY_LIMIT_USD = 3.0
DAILY_LIMIT_USD = 15.0

# 変更後
HOURLY_LIMIT_USD = 3.0        # 変更なし
DAILY_SOFT_LIMIT_USD = 6.0    # 新規追加: 警告のみ（停止しない）
DAILY_LIMIT_USD = 8.0         # 変更: 15.0 → 8.0（即停止）
```

## 2. disable_tasks()の拡張

```python
def disable_tasks():
    tasks = [
        'SES_MailPipeline',
        'SES_MatchingAndNotify',    # 既存（無効化済タスクだがそのまま残す）
        'SES_MatchingV3',           # 新規追加: アクティブなマッチャー
        'jobz_importer',            # 新規追加: attachment importer
        'SES_Outlook_9h',           # 新規追加
        'SES_Outlook_13h',          # 新規追加
        'SES_Outlook_18h',          # 新規追加
    ]
    for t in tasks:
        result = subprocess.run(
            ['schtasks', '/Change', '/TN', t, '/DISABLE'],
            capture_output=True, text=True
        )
        print(f"Disabled {t}: returncode={result.returncode}")
```

## 3. kill_cloud_run()の新規追加

```python
def kill_cloud_run():
    """Cloud RunのLLM呼び出しをenv varで無効化する"""
    try:
        result = subprocess.run(
            [
                'gcloud', 'run', 'services', 'update', 'line-webhook',
                '--region', 'asia-northeast1',
                '--update-env-vars', 'LLM_KILL=1',
                '--project', 'ses-work-automation',
                '--quiet',
            ],
            capture_output=True, text=True, timeout=120
        )
        print(f"Cloud Run kill: returncode={result.returncode} stdout={result.stdout[:200]}")
    except Exception as e:
        print(f"Cloud Run kill error: {e}")
```

## 4. main()の3段階制御に変更

```python
def main():
    hourly, daily = get_costs()
    print(f"過去1時間: ${hourly:.4f} / 過去24時間: ${daily:.4f}")

    if daily >= DAILY_LIMIT_USD:
        msg = (
            f"⚠️ APIコスト上限到達（ハード停止）\n"
            f"過去24時間: ${daily:.2f}（上限${DAILY_LIMIT_USD}）\n"
            f"SES全タスク + Cloud Runを停止しました"
        )
        print(f"[ALERT-HARD] {msg}")
        disable_tasks()
        kill_cloud_run()
        send_line(msg)

    elif daily >= DAILY_SOFT_LIMIT_USD:
        msg = (
            f"⚠️ APIコスト警告（ソフト）\n"
            f"過去24時間: ${daily:.2f}（警告閾値${DAILY_SOFT_LIMIT_USD}）\n"
            f"自動停止はしていません。要確認"
        )
        print(f"[WARN-SOFT] {msg}")
        send_line(msg)

    elif hourly >= HOURLY_LIMIT_USD:
        msg = (
            f"⚠️ APIコスト急増\n"
            f"過去1時間: ${hourly:.2f}（閾値${HOURLY_LIMIT_USD}）\n"
            f"要確認"
        )
        print(f"[WARN-HOURLY] {msg}")
        send_line(msg)

    else:
        print("OK: コスト正常範囲内")
```

## 完成形の要件
- disable_tasks() に7タスクが含まれている
- kill_cloud_run() 関数が存在する
- DAILY_SOFT_LIMIT_USD = 6.0 が定義されている
- DAILY_LIMIT_USD = 8.0 に変更されている
- main()が3段階（HARD/SOFT/HOURLY）で動作する
- バックアップファイル cost_guard.py.bak_phase1 が存在する
- py_compileが通る
