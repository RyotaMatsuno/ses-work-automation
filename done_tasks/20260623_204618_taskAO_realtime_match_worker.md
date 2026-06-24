# 【Cursor作業指示】Task AO: 案件受信3時間以内の自動マッチングフロー

対象: ses_work/matching_v3/ + ses_work/mail_pipeline.py
参照: CLAUDE.md / 判断マニュアルv3.md（案件タイマー参照）
完了条件: 新規案件登録から3時間以内に候補リストが自動生成される

## 変更
1. mail_pipeline.pyの案件Notion登録完了時にmatching_statusを"pending"に設定
2. worker/realtime_match_worker.py 新規作成:
   - 5分おきに「matching_status=pending AND 受信3時間以内」の案件をNotion DBからフェッチ
   - 該当案件に対してmatching_v3のjudge()をインラインで実行
   - MATCH候補をmatching_statusを"matched"に更新
   - 松野公式LINEに「新規案件: {案件名} → MATCH {N}名」を通知
3. Windowsタスクスケジューラに5分おき実行を登録
4. 重複防止: project_id + dateベースのidempotency key
5. 案件タイマー準拠: 通常3h、急募2h、中長期6h（判断マニュアルv3のルール）

## 注意
- LINE push通知の月200通制限を考慮（push_or_log使用）
- CostGuardなしでLLMを呼び出さない
