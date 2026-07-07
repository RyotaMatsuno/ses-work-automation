# auto_runner通知ダイジェスト化 + target_file誤NG修正（松野指示 2026-07-06）

## 背景
- auto_runnerのNG/再投入通知が松野公式LINEへ逐次pushされ多すぎる（松野指示: 1日2回まとめ報告でよい）
- 「target_file not found:（値が空）」による誤NG→再投入が頻発
  （実例: 20260706_165126はtry2まで消費、20260706_報酬4軸も同一理由でtry2突入）
  target_file未指定タスクの検証ロジック不具合の疑い

## 修正1: 通知ダイジェスト化（task_auto_runner/）
1. 逐次pushを廃止。イベント（NG/再投入/完了/blocked移動）は
   task_auto_runner/notify_queue.jsonl に追記するだけにする
2. 12:00 / 18:00 JST の2回、キューをまとめて1通で送信（push_or_log経由・LINE残通数チェック維持）
   書式例: 「[runner 12:00] 完了3 / 再投入1 / blocked 0」+ タスク名を各1行
3. イベント0件の回は送信しない（200通/月上限の温存）
4. 即時通知の例外は設けない（松野はLINE「作業進捗」でいつでもpull可能）
5. 送信済みイベントはキューから消し込み（多重送信防止）

## 修正2: target_file誤NGの根本対処
1. 原因調査: タスクmdにtarget_file指定が無い/空の場合の検証パスを特定
2. target_fileを任意項目化。未指定・空なら検証をスキップし、NG扱いにしない
3. 既存のリトライ（try1/try2→blocked）ロジック自体は変更しない

## テスト（task_auto_runner/tests/）
- イベント集約→12:00/18:00トリガーで1通化 / 0件時スキップ / 消し込み
- target_file未指定タスクがNGにならないこと（回帰: 空文字・項目欠落の両方）

## 完了後
python gate_checker/gate_check.py --phase implementation --file <変更した主ファイル>
※ ゲートは7/7の日次リセット後に実行（7/6は30/30到達済み）

## 禁止事項
- 松野公式LINE以外のチャンネルから送信しない
- LLM呼び出し不要（ルールベースのみ）
