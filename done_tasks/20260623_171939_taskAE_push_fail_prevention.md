# 【Cursor作業指示】Task AE: nightly_jobzキューへのpush_fail投入防止（P1）

対象ディレクトリ: ses_work/line_webhook/ および ses_work/nightly_jobz/
作業内容: LINE push失敗時にAI作業キューDBにpush_failレコードが投入される問題の根本修正
参照ファイル: CLAUDE.md / line_bridge.py / nightly_jobz/notion_queue.py
完了条件: push失敗時にキューではなくエラーログのみに記録される

---

## 問題
- LINE push失敗イベントがNotion AI作業キューDBにtype=devとして投入されていた
- nightly_jobzはPhase 1未対応のためblocked処理するだけで、キューが汚染される
- 6/19〜6/23で46件のpush_failレコードが蓄積（今回手動アーカイブ済み）

## 修正方針（GPT-5.4合意済み）
1. line_bridge.py内のpush失敗ハンドラを特定し、キュー投入ではなくログファイル記録に変更
2. push_failはses_work/logs/push_errors.logなど専用ログに書き出す
3. nightly_jobz側にもallowlist制御を追加: 投入時にtype='dev'かつtask_idが'push_fail'のパターンは拒否
4. 既存のpush_fail投入経路を全て洗い出して塞ぐ

## 調査ポイント
- line_bridge.pyの中でNotion API POST（ページ作成）を呼んでいる箇所を特定
- push失敗時のフォールバック処理を追跡
- push_or_log()関数の実装を確認

## 禁止事項
- 正常なキュー投入ロジック（マッチング/営業/経理タスク）に影響を与えない
- LINE push成功時の動作を変更しない
