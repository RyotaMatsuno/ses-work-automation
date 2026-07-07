# 【最優先】gate通知のダイジェスト統合 + ゲート連打ガード（松野指示 2026-07-07）

事象: エージェントが1タスク試行内で「修正→gate→NG」を短時間ループし
（delete_zero_ref_canonicals.py に12:48〜12:58で7回、test_secret_scan.py に13:06〜13:07で3回）、
NGごとにLINE即時通知が発火。松野指示「多すぎる、減らして」。

## 修正1: gate_check.py のLINE即時通知を全廃
- NG/GO問わずLINE pushを行わない。イベントは task_auto_runner/notify_queue.jsonl に追記のみ
  （runner_notify_digest と同一キュー・同一フォーマット。12:00/18:00ダイジェストに載る）
- 例外なし。CostGuard停止（exit 2）系の handle_costguard_blocked 内の通知も同様にキュー行きへ
- 「作業進捗」LINEコマンドでのpull確認は現状維持

## 修正2: ゲート連打ガード（gate_check.py）
- 同一target_fileへの同日NGが3回に達したら、以降の同targetゲートは即 exit 2
  （メッセージ: 「本日NG3回到達。修正内容を見直しblocked化を検討」）+ キューにイベント記録
- daily_counter とは別に results/ 配下に per-target カウンタを持つ（日付でリセット）

## 修正3: エージェント指示テンプレの改訂（task_auto_runner）
- タスク実行プロンプトに追記: 「gate_check実行は1タスク試行あたり最大3回。
  3回NGの場合は修正を中断し、NG理由を要約してタスクをblockedへ」

## テスト
- NG時にLINE pushが発生しないこと / キュー追記されること
- 同一target 3NG後の即exit 2
- 既存のdaily_counter(30回)ロジックに影響しないこと

## 完了後
python gate_checker/gate_check.py --phase implementation --file gate_checker/gate_check.py
※ 本日のゲート残数を考慮し、このタスク自体のゲートは1回のみ。NGでも再修正ループ禁止
　（NG理由をログに残してblockedへ。ジョブズが翌チャットで判断）
