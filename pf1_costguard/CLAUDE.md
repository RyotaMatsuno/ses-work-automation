# CLAUDE.md - Phase1: cost_guard緊急対応

## 目的
グローバルキルスイッチが止血できていない構造を修正する。
全LLMコンポーネントを止められるよう対象を拡張し、監視をグローバル合算に変更する。

## 絶対禁止
- ses_work以下のcost_guard.py以外のファイルは変更しない（mail_pipeline・matching_v3は触らない）
- 既存のログ・JSONLファイルは消さない
- スクリプト名・関数名の公開I/Fは変えない

## 注意
- `schtasks` コマンドはWindowsターミナルで動く
- gcloudコマンドはPATHに入っている
- LINE通知トークンは os.environ['LINE_CHANNEL_ACCESS_TOKEN'] から取得
- 松野user_id: Ue3508b43b84991f5a68281da5bf4cf39
