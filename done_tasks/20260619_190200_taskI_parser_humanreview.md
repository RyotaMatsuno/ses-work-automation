# 【Cursor作業指示】Task I: パーサー改善（備考日数分岐 + human_reviewキーワード）

対象ディレクトリ: ses_work/
作業内容: マッチング精度改善 + ゲートチェッカー精度改善
完了条件: 日数分岐実装 + キーワード追加 + テスト
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 修正1: 備考フォールバック結果待ち日数分岐（#11）

### 対象ファイル
matching_v3/matcher.py の _calc_parallel_score()

### 問題
結果待ちスコアが2.0固定。判断マニュアルの分岐が効いていない:
- 結果待ち(1-2日): 2.5
- 結果待ち(3-7日): 2.0
- 結果待ち(8日+): 0

### 修正方針
備考テキストから結果待ち日数を推定するパーサーを追加:

```python
import re
from datetime import datetime, timedelta

def _extract_result_wait_days(remark: str) -> int | None:
    """備考テキストから結果待ち日数を推定"""
    # パターン1: 「結果待ち 6/15」「結果待ち（6月15日）」
    m = re.search(r'結果待ち.*?(\d{1,2})[/月](\d{1,2})', remark)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        now = datetime.now()
        interview_date = now.replace(month=month, day=day)
        if interview_date > now:
            interview_date = interview_date.replace(year=now.year - 1)
        days = (now - interview_date).days
        return max(0, days)

    # パターン2: 「結果待ち」のみ（日付なし）→ 不明
    if '結果待ち' in remark:
        return None  # 不明→デフォルト2.0を維持

    return None

def _result_wait_score(days: int | None) -> float:
    if days is None:
        return 2.0  # 不明時はデフォルト
    if days <= 2:
        return 2.5
    if days <= 7:
        return 2.0
    return 0.0  # 8日以上はカウントなし
```

_calc_parallel_score() 内で「結果待ち」検出時に上記関数を呼ぶ。

### テスト
- 「結果待ち 6/18」（1日前）→ 2.5
- 「結果待ち 6/15」（4日前）→ 2.0
- 「結果待ち 6/1」（18日前）→ 0.0
- 「結果待ち」（日付なし）→ 2.0（デフォルト）

---

## 修正2: needs_human_review層1キーワード追加（#17）

### 対象ファイル
gate_checker/gate_check.py の needs_human_review()

### 問題
層1キーワードに「費用が発生」「契約変更」が未登録。
層3のHUMAN_REVIEW行欠落時のフォールバックなし。

### 修正方針
```python
LAYER1_KEYWORDS = [
    "費用が発生", "契約変更",  # 追加
    "岡本に連絡", "根本設計変更",
    "法人化", "TERRA依存",
    # 既存キーワード...
]

# 層3フォールバック追加
def needs_human_review(text: str) -> bool:
    # 層1: 完全一致キーワード
    for kw in LAYER1_KEYWORDS:
        if kw in text:
            return True
    # 層2: 類義語辞書
    for synonym, canonical in SYNONYM_MAP.items():
        if synonym in text and canonical in LAYER1_KEYWORDS:
            return True
    # 層3: GPT自己判定
    try:
        gpt_result = _gpt_human_review_check(text)
        if "HUMAN_REVIEW" in gpt_result:
            return True
    except Exception:
        # 層3失敗時のフォールバック: 安全側に倒す（要確認）
        return True
    return False
```

### テスト
- 「費用が発生します」→ True
- 「契約変更が必要」→ True
- 「コストが増える」（類義語）→ True（類義語辞書に「コスト」→「費用が発生」を追加）
- 層3失敗時→ True（安全側）

---

## 共通ルール
- 既存テスト全パス / 新規コードにtype hint
