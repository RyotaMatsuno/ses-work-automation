# 【Cursor作業指示】Task BB: 分類ラベル正規化（非標準ラベル吸収）

対象ファイル: ses_work/mail_pipeline/mail_pipeline.py
作業内容: LLM出力の非標準分類ラベルを正規ラベルにマッピング
参照ファイル: CLAUDE.md
完了条件: talent/resume/resource等が正規ラベルに変換される
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 背景
- 分類LLM（Claude Haiku）が稀に非標準ラベルを返す（6件/日程度）
- 確認済みの非標準ラベル: talent, resume, resource, recruitment, personnel
- これらは正規ラベル（project/engineer/skip/other）に該当するが未処理のまま

## 変更内容

### 1. 正規化マッピング辞書を追加（mail_pipeline.py冒頭の定数セクション）
```python
LABEL_NORMALIZE_MAP = {
    # engineer系
    "talent": "engineer",
    "resume": "engineer",
    "resource": "engineer",
    "personnel": "engineer",
    "recruitment": "engineer",
    "candidate": "engineer",
    "human_resource": "engineer",
    "staff": "engineer",
    # project系
    "job": "project",
    "position": "project",
    "requirement": "project",
    "opening": "project",
    # skip系
    "spam": "skip",
    "newsletter": "skip",
    "advertisement": "skip",
}
```

### 2. 分類結果のpost-processing
- classify_email_v2() のBatch API応答パース後に正規化を適用
- `result.get("type", "").lower().strip()` → LABEL_NORMALIZE_MAPで変換
- 未知ラベル（マップにない非標準値）は "other" に変換
- 正規ラベルリスト: {"project", "engineer", "skip", "other"}

### 3. ログ出力
- 変換が発生した場合: `[LABEL_NORM] "{元ラベル}" → "{正規ラベル}" (msg_id={id})`
- 監視用に変換件数をメトリクスに含める

## テスト
1. 各非標準ラベルが正しく変換されることの単体テスト
2. 未知ラベル → "other" への変換テスト
3. 正規ラベル（project/engineer/skip/other）はそのまま通過
4. 既存テスト全PASS

---

## 完了メモ (2026-06-24)
- `LABEL_NORMALIZE_MAP` / `normalize_classify_label()` / `_normalize_classify_results()` 追加
- `classify_email_v2` Batch後に正規化、`label_norm_count` メトリクス
- `mail_pipeline/tests/test_task_bb_label_normalize.py` 7件パス
