# 【Cursor作業指示】011_mail_keyword_classify v4実装

作成日: 2026-06-16
優先度: P0（コスト直結）
ステータ: dry-run検証済み（230件・LLM削減率63.9%確認済み）

---

## 背景・検証結果

230件dry-runで以下を確認済み:
| カテゴリ | 件数 | 割合 |
|---|---|---|
| project（キーワード確定） | 36件 | 15.7% |
| engineer（キーワード確定） | 109件 | 47.4% |
| skip（非案件確定） | 2件 | 0.9% |
| None（LLM必要） | 83件 | 36.1% |

LLM削減率: 63.9%
4,580件/日 → LLM必要: 約1,653件（従来4,580件→63.9%削減）

誤分類: 1件（「Java案件ください！弊社プロパー」→engineer判定、実質正解）

---

## 対象ファイル

`ses_work/mail_pipeline/mail_pipeline.py`

存在確認コマンド（実装前に必ず実行）:
```python
import os
p = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\mail_pipeline.py'
print("EXISTS:", os.path.exists(p))
```

---

## タスク1: classify_subject_keyword 関数を追加

mail_pipeline.py の先頭インポート部の直後（定数定義エリア）に以下を追加:

```python
# ========== 件名キーワード事前分類（LLM不使用・v4確定版） ==========
# dry-run 230件検証済み: LLM削減率63.9%

SUBJECT_SKIP_PATTERNS = [
    "請求書", "注文書", "発注書", "見積書", "見積もり", "御見積",
    "納品書", "領収書", "勤務表", "勤怠", "稼働報告", "工数",
    "契約書", "覚書", "基本契約", "業務委託契約", "秘密保持",
    "支払", "入金", "振込", "口座", "押印", "捺印",
    "年末調整", "源泉", "インボイス", "適格請求書",
    "セミナー", "ウェビナー", "イベント", "勉強会", "登壇",
    "メンテナンス", "障害通知", "障害復旧", "アップデート通知",
    "おめでとう", "新年", "年始", "年末", "夏季休業", "休業",
    "アンケート", "ニュースレター", "メルマガ", "配信停止",
]
SUBJECT_PROJECT_PATTERNS = [
    "案件", "募集", "求人", "BP案件",
    "★案件", "■案件", "【案件",
    "万円", "万／",
    "リモート案件", "常駐案件", "PMO案件", "インフラ案件",
]
SUBJECT_ENGINEER_PATTERNS = [
    "弊社社員", "弊社正社員", "弊社プロパー", "弊社フリーランス",
    "弊社エンジニア", "弊社技術者", "自社社員",
    "弊社直", "弊社増員", "弊社候補",
    "要員",
    "技術者のご紹介", "エンジニアのご紹介",
    "経歴書", "スキルシート", "プロパー",
    "営業中", "稼働可能",
    "ご紹介です", "のご紹介", "さんのご紹介",
    "人材】", "おすすめ人材",
    "歳】男性", "歳】女性", "歳／男性", "歳／女性",
    "実務", "年超／", "年以上／",
    "経験", "年・",
]


def classify_subject_keyword(subject: str) -> str | None:
    """件名キーワードで事前分類（LLM不使用）。
    戻り値: "project" | "engineer" | "skip" | None（判断不能→LLMへ）
    v4確定版: dry-run 230件で63.9%削減確認済み（2026-06-16）
    """
    if not subject:
        return None
    s = subject
    # 1. 非案件スキップ（最優先）
    for kw in SUBJECT_SKIP_PATTERNS:
        if kw in s:
            return "skip"
    # 2. ヒット数算出
    eng_hit = sum(1 for kw in SUBJECT_ENGINEER_PATTERNS if kw in s)
    prj_hit = sum(1 for kw in SUBJECT_PROJECT_PATTERNS if kw in s)
    # 3. 「案件」は単独で project 確定（engineerキーワードがない場合）
    if "案件" in s and eng_hit == 0:
        return "project"
    # 4. engineer 優先（1件以上かつ project より多い）
    if eng_hit >= 1 and eng_hit > prj_hit:
        return "engineer"
    # 5. project（2件以上かつ engineer より多い）
    if prj_hit >= 2 and prj_hit > eng_hit:
        return "project"
    # 6. 判断不能 → LLMへ
    return None
# ========== /件名キーワード事前分類 ==========
```

---

## タスク2: classify_email_v2（またはメイン処理ループ）へ組み込み

メール処理ループの先頭（LLM分類呼び出しの直前）に以下を追加:

```python
# 件名キーワード事前分類（LLMコスト削減）
_kw_subject = em.get("subject", "") or ""
_kw_type = classify_subject_keyword(_kw_subject)
if _kw_type == "skip":
    log(f"[KW-SKIP] {_kw_subject[:60]}")
    kw_skip_count += 1
    continue
elif _kw_type in ("project", "engineer"):
    log(f"[KW-{_kw_type.upper()}] {_kw_subject[:60]}")
    kw_decided_count += 1
    # 分類を確定してLLM抽出フェーズへ直接進む
    em["_kw_type"] = _kw_type
    # ← 既存の詳細抽出処理にそのまま渡す（分類LLM呼び出しはスキップ）
# _kw_type is None → 従来通りLLM分類へ（フォールスルー）
```

カウンター変数を関数スコープ内で初期化:
```python
kw_skip_count = 0
kw_decided_count = 0
llm_classify_count = 0
```

---

## タスク3: コスト効率ログ出力

メイン処理の最後に追加:
```python
log(f"[コスト効率] LLM分類: {llm_classify_count}件 / KWスキップ: {kw_skip_count}件 / KW確定: {kw_decided_count}件 / 削減率: {(kw_skip_count+kw_decided_count)/(kw_skip_count+kw_decided_count+llm_classify_count+0.001)*100:.1f}%")
```

---

## タスク4: FETCH_LIMITを引き上げ（dry-run後に本番適用）

※今週は変更しない。金曜の本番50件確認後に適用。
コメントアウト状態で追記だけしておく:
```python
# FETCH_LIMIT = 1500  # TODO: 2026-06-20以降に有効化（キーワード分類で63.9%削減確認済み）
# CLASSIFY_LIMIT = 1500
```

---

## テスト（実装後に必ず実行）

```python
# 単体テスト
import sys
sys.path.insert(0, r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work')
from mail_pipeline.mail_pipeline import classify_subject_keyword

test_cases = [
    ("【BTM案件】AWS移行エンジニア募集", "project"),
    ("【弊社社員】Java8年 即日可", "engineer"),
    ("7月分御見積書のご送付", "skip"),
    ("【ウェビナー】AI活用最前線", "skip"),
    ("★弊社直個人事業主★Python(1年)", "engineer"),
    ("急募！ITディレクター", None),
]
errors = 0
for subject, expected in test_cases:
    result = classify_subject_keyword(subject)
    status = "OK" if result == expected else "NG"
    if status == "NG":
        errors += 1
    print(f"[{status}] '{subject[:40]}' → {result} (期待:{expected})")
print(f"\n結果: {len(test_cases)-errors}/{len(test_cases)} 通過")
```

---

## ゲート

実装完了後:
```
cd ses_work
python gate_checker/gate_check.py --phase implementation --file mail_pipeline/mail_pipeline.py
```

GO判定後、「メールキーワード分類完了」とClaude.aiに報告。

---

## 注意事項

- blocked理由「target_file not found」は、Cursorがパスを動的に解決できなかったため
- mail_pipeline.pyのフルパスは: `C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\mail_pipeline.py`
- 実装前に `os.path.exists()` でファイル存在を必ず確認すること
- CostGuard必須（共通ledger.py経由）
- 今週は FETCH_LIMIT を変更しない（タスク4はコメントのみ）
