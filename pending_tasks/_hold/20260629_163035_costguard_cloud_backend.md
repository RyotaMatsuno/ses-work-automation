# 案B: CostGuard Cloud Backend（低優先・バックグラウンド）

## 目的
CostGuardのstate backendをCloud Run互換にする。
現在のSQLite（ローカル専用）→ Firestore or Cloud SQL に移行。
完成したら案A（COST_GUARD_DISABLED）を解除して移行。

## 要件
1. cost_guard.py にbackend抽象化レイヤーを追加
   - LocalSqliteBackend（現行動作を維持）
   - FirestoreBackend（Cloud Run用）
2. 環境変数 COST_GUARD_BACKEND=sqlite|firestore で切替
3. Firestore collection: ses_cost_guard/daily_state, monthly_state, event_log
4. allowed()/finalize() のインターフェースは変更しない
5. 冪等設計: finalize()失敗→リトライで二重計上しない
6. Cloud Run複数インスタンスでstate分裂しない

## 制約
- Firestoreの無料枠内で運用（1日20K read / 20K write）
- 既存のローカル動作（gate_check, mail_pipeline）を壊さない
- CostGuardのテスト全PASSを維持

## 3点セット
- cost_guard_v2/CLAUDE_cloud_backend.md（作成必要）
- cost_guard_v2/SPEC_cloud_backend.md（作成必要）
- cost_guard_v2/TASKS_cloud_backend.md（作成必要）

## 移行手順（完成後）
1. Firestore設定 + サービスアカウント権限追加
2. Cloud Runに COST_GUARD_BACKEND=firestore を設定
3. COST_GUARD_DISABLED=1 を削除
4. ローカルは COST_GUARD_BACKEND=sqlite（デフォルト）のまま

## 優先度
低（タスクがない時にバックグラウンドで進める）
