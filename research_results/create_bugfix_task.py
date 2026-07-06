import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import os
from datetime import datetime

PENDING = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pending_tasks"
ts = datetime.now().strftime("%Y%m%d_%H%M%S")

task = f"""【Cursor作業指示】
対象ディレクトリ: ses_work/
作業内容: Pilot発見バグ3件修正 + 安全スキャン + 全20件リプレイ検証
参照ファイル: CLAUDE.md / extractors/ / scripts/backfill_engine.py / golden_test/
完了条件: 3バグ修正 + 全20件リプレイPASS + 安全スキャンPASS + 回帰テストPASS

## 背景
Pilot 20件で3バグ+1軽微を発見。GPT-5.4レビュー済み。バッチbackfill前に修正・検証する。

---

## 修正1: rate単位変換バグ（最優先）

### 症状
「単価：55万」→ Notionに550,000で格納された。

### 根本原因
extractor→backfill_engineのwrite pathで万→円変換が混入している。

### 修正方針
**extractors/rate_extractor.pyの出力は常に万単位の整数。write pathに変換ロジックを入れない。**

1. `rate_extractor.py`: 出力のrate_min_man / rate_max_man は**万単位の数値**（55, 70, 120等）
2. `scripts/backfill_engine.py`: Notion書き込み時に**変換しない**。extractorの出力をそのままNotionのnumberフィールドに書く
3. write前バリデーション追加:
```python
def validate_rate_before_write(rate_value):
    if rate_value is None:
        return True
    if rate_value > 200:
        raise ValueError(f"Rate {rate_value}万 exceeds 200万 limit - likely unit conversion bug")
    if rate_value < 0:
        raise ValueError(f"Negative rate: {rate_value}")
    return True
```
4. **全コードパスを検索**: `* 10000` / `* 10_000` / `万` の計算箇所を全て確認し、不要な変換を削除

---

## 修正2: rate_extractorパターン拡張

### 症状
- 「70万（スキル見合い）」→ skill_dependent_no_number（数値を拾えていない）
- 「50万円前後」→ unknown（パターン未対応）

### 修正: regex Pass 1 のパターン追加（優先度順に挿入）

**現行パターン順序を以下に更新:**

```python
RATE_PATTERNS = [
    # 1. レンジ（最優先）
    (r'(\\d{{2,3}})\\s*万円?\\s*[〜～\\-~]\\s*(\\d{{2,3}})\\s*万', 'fixed_range', 0.90),
    
    # 2. スキル見合い + 数値（前後どちらの語順でも）
    (r'スキル見合.*?(?:MAX|max|Max|上限|〜|~|～|まで)?\\s*(\\d{{2,3}})\\s*万', 'skill_dependent_with_cap', 0.90),
    (r'(\\d{{2,3}})\\s*万円?.*?(?:スキル見合|経験見合|応相談)', 'skill_dependent_with_cap', 0.85),
    
    # 3. MAX/上限
    (r'(?:MAX|max|Max|上限)\\s*[:：]?\\s*(\\d{{2,3}})\\s*万', 'fixed_upper_only', 0.85),
    (r'[〜～~]\\s*(\\d{{2,3}})\\s*万', 'fixed_upper_only', 0.80),
    (r'(\\d{{2,3}})\\s*万円?\\s*(?:まで|以下|以内)', 'fixed_upper_only', 0.80),
    
    # 4. 概算（前後/程度/目安/想定）
    (r'(\\d{{2,3}})\\s*万円?\\s*(?:前後|程度|目安|想定)', 'fixed_upper_only', 0.70),
    
    # 5. 単純数値（単価/予算/金額の文脈内）
    (r'(?:単価|予算|金額|報酬)\\s*[:：]\\s*(\\d{{2,3}})\\s*万', 'fixed_upper_only', 0.75),
    
    # 6. スキル見合い（数値なし）
    (r'スキル見合|経験見合|ご経験見合|スキル次第', 'skill_dependent_no_number', 1.0),
    (r'応相談', 'skill_dependent_no_number', 0.80),
]
```

### 全角数字対応
パターンマッチ前にテキストを正規化:
```python
def normalize_text(text):
    # 全角数字→半角
    text = text.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
    # 全角スペース→半角
    text = text.replace('　', ' ')
    return text
```

### マッチ窓の制限
`.*?`の暴走防止。各パターンは**100文字以内の窓**でマッチさせる:
```python
# 全文を100文字窓でスライスして各パターンを試行
for i in range(0, len(text), 50):  # 50文字刻みで重複走査
    window = text[i:i+100]
    for pattern, rate_type, conf in RATE_PATTERNS:
        match = re.search(pattern, window)
        if match:
            ...
```

---

## 修正3: remote_extractor「初日出社」対応

### SES業界セマンティクス（GPT-5.4確認済み）
「初日出社」= フルリモート案件で初日のみ出社（PC受取/顔合わせ）。**hybridではない。**

### 修正方針
**full_remoteのまま維持 + initial_onsite_required=Trueフラグ追加**

```python
@dataclass
class RemoteResult:
    remote_type: str
    onsite_days_per_week: int | None
    initial_onsite_required: bool  # ← 追加
    confidence: float
    method: str
    evidence: str | None
    needs_llm_fallback: bool
```

### 一時出社パターン（full_remote維持）
```python
INITIAL_ONSITE_PATTERNS = [
    r'初日出社', r'初月出社', r'立ち上がり出社', r'参画初日出社',
    r'初回出社', r'初日のみ出社', r'入場初日出社',
    r'セットアップ時出社', r'PC受取.*出社', r'貸与物受取.*出社',
]
```
→ これらがヒットした場合: `initial_onsite_required=True`。remote_typeは変更しない。

### 定期出社パターン（hybrid判定）
```python
RECURRING_ONSITE_PATTERNS = [
    r'週\\d.*出社', r'月\\d+回出社', r'必要時出社', r'月1出社',
]
```
→ これらがヒットした場合: `remote_type=hybrid`。既にfull_remoteだったらhybridに上書き。

### 処理順序
1. 一次分類（既存ロジック: full_remote/hybrid/onsite/remote_possible/unknown）
2. 一時出社チェック → initial_onsite_required設定（remote_type変更なし）
3. 定期出社チェック → remote_type=hybridに上書き（矛盾解消）

---

## 追加作業: 安全スキャン

### Notion全レコードスキャン: scripts/safety_scan.py
募集中の全案件で以下をチェック:
```python
ANOMALY_CHECKS = [
    ("rate > 200", lambda p: (p.get("単価（万円）") or 0) > 200),
    ("rate > 1000 (unit bug)", lambda p: (p.get("単価（万円）") or 0) > 1000),
    ("rate == 0 残り", lambda p: p.get("単価（万円）") == 0),
    ("skill_dep_no_num but source has number", ...),  # 案件詳細にN万がありながらskill_dependent_no_number
    ("full_remote but 初日出社", ...),  # full_remoteで初日出社パターンあり
]
```
出力: anomaly_report.csv（page_id, anomaly_type, current_value, source_context）

---

## 検証: 全20件リプレイ

### 手順
1. pilot 19件（v2タグ付き）の現在値をスナップショット
2. 修正版extractorで全19件を再抽出
3. before/after diff出力
4. **15件の正常ケースに変化がないこと確認**（回帰テスト）
5. **3件のバグケースが修正されたこと確認**
6. **1件のminorケースが改善されたこと確認**

### 回帰テスト追加
golden_test/regression_test.py に以下テストケースを追加:
- 「70万（スキル見合い）」→ skill_dependent_with_cap, rate_max=70
- 「単価：55万」→ rate_max=55（550000ではない）
- 「フルリモート...初日出社有」→ full_remote + initial_onsite=True
- 「50万円前後」→ fixed_upper_only, rate_max=50

---

## 禁止事項
- 既存の必要スキル/尚可スキル抽出ロジック変更
- 15件の正常ケースの出力を変えること
- dry-runなしでNotionへの書き込み
- rate値に10000を掛ける変換

## 完了条件チェックリスト
- [ ] rate_extractor.py パターン拡張完了
- [ ] rate write pathの単位変換バグ修正
- [ ] remote_extractor.py initial_onsite_required追加
- [ ] scripts/safety_scan.py 実行 → 異常レポート出力
- [ ] 全20件リプレイ diff確認
- [ ] 15件正常ケースに変化なし（回帰PASS）
- [ ] 3件バグケース修正確認
- [ ] golden_test/regression_test.py に4テスト追加 → PASS
"""

fpath = os.path.join(PENDING, f"04a_{ts}_bugfix_replay_scan.md")
with open(fpath, 'w', encoding='utf-8') as f:
    f.write(task)

print(f"Created: {os.path.basename(fpath)}")
print("DONE")
