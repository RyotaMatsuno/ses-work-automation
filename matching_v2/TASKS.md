# TASKS.md - matching_v2 精度改善 v3

## タスクリスト

- [ ] 1. pip install jpholiday --break-system-packages（未インストールなら）
- [ ] 2. matching_v2.py: get_min_gross(engineer_owner, project_owner)関数を追加
- [ ] 3. matching_v2.py: evaluate_candidate()内の粗利チェックをget_min_gross()に変更
- [ ] 4. mail_pipeline.py: jpholidayをimport、is_within_business_days()関数を追加
- [ ] 5. mail_pipeline.py: 案件タイマーロジックを削除し、is_within_business_days(n=4)による有効期限チェックに差し替え
- [ ] 6. mail_pipeline.py: 面談設定済み案件（interview_datetimeあり）の有効期限スキップを実装（面談1時間前まで有効）
- [ ] 7. py_compile matching_v2/matching_v2.py
- [ ] 8. py_compile mail_pipeline.py
- [ ] 9. python -c "from matching_v2.matching_v2 import get_min_gross; assert get_min_gross('岡本','松野')==3; assert get_min_gross('松野','松野')==5; print('OK')"
