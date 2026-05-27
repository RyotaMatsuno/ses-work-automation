# SPEC.md - matching_v2 精度改善 v3

最終更新: 2026-05-26

## 改善1: 担当者別最低粗利閾値（matching_v2.py）

### 目的
岡本担当案件・エンジニアのマッチングは粗利3万円（TERRAより低い契約条件を考慮）。
松野担当は従来通り5万円。クロス案件は低い方（3万）を採用。

### 実装
```python
def get_min_gross(engineer_owner, project_owner):
    # 担当者不明は安全側で5万
    if not engineer_owner or not project_owner:
        return 5
    # どちらかが岡本なら3万
    if "岡本" in (engineer_owner or "") or "岡本" in (project_owner or ""):
        return 3
    return 5
```

- `evaluate_candidate()`内の粗利チェックで `get_min_gross(engineer_owner, project_owner)` を使用
- engineer_owner: エンジニアDBの「担当者」フィールド
- project_owner: 案件DBの「担当者」フィールド

---

## 改善2: 案件有効期限チェック（mail_pipeline.py）

### 目的
案件タイマー（受信から3時間/2時間/6時間）を廃止し、4営業日以内の案件のみ処理対象とする。
日本の祝日（jpholiday）を考慮した営業日カウントに変更。

### 実装
```python
import jpholiday
def is_within_business_days(created_time, n=4):
    today = datetime.now().date()
    count = 0
    d = created_time.date()
    while d <= today:
        if d.weekday() < 5 and not jpholiday.is_holiday(d):
            count += 1
        d += timedelta(days=1)
    return count <= n
```

- 面談設定済み案件（interview_datetimeあり）は有効期限チェックをスキップ
- 面談設定済み案件は面談1時間前まで有効

---

## 改善3: double_check.pyの粗利チェック更新

- 粗利チェックを `get_min_gross()` ベースに変更（担当者別閾値を参照）

---

## 完了条件
1. py_compile matching_v2/matching_v2.py → エラーなし
2. py_compile mail_pipeline.py → エラーなし
3. python -c "from matching_v2.matching_v2 import get_min_gross; print(get_min_gross('岡本','松野'))" → 3
4. python -c "from matching_v2.matching_v2 import get_min_gross; print(get_min_gross('松野','松野'))" → 5
5. jpholiday import確認
